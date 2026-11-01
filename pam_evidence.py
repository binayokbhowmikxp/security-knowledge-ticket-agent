"""Evidence/citation reporting after a PydanticAI run; no model calls or logging."""
import re

from pydantic_ai.messages import RetryPromptPart, ToolCallPart, ToolReturnPart


DISCLAIMER = 'Synthetic training guidance; not official vendor documentation.'
# Keep evidence kinds tied to the tool that actually returned each record.
SOURCE_TYPES = {
    'search_documentation': ('id', r'(?:ONB|ROT|WEB)-\d{3}', 'documentation'),
    'get_asset_details': ('asset_id', r'(?:LNX|WIN|APP)-\d{3}', 'current asset'),
    'search_past_tickets': ('ticket_id', r'TKT-\d{3}', 'historical ticket'),
}
SOURCE_PATTERN = r'(?:ONB|ROT|WEB|LNX|WIN|APP|TKT)-\d{3}'
VALIDATION_REASON_CODES = frozenset({
    'missing_citation', 'unretrieved_citation', 'invalid_citation_format',
    'missing_disclaimer', 'unsupported_documentation_guidance',
})


def returned_ids(tool_name, content):
    """Extract only normal IDs from successful record objects, never prose."""
    if tool_name not in SOURCE_TYPES:
        return []
    key, pattern, _ = SOURCE_TYPES[tool_name]
    records = content if isinstance(content, list) else [content]
    ids = set()
    for record in records:
        if not isinstance(record, dict) or 'error' in record:
            continue
        value = record.get(key)
        if isinstance(value, str) and re.fullmatch(pattern, value):
            ids.add(value)
    return sorted(ids)


def collect_evidence(messages):
    """Pair actual tool returns with pending calls by ID and name.

    Trace sequence reflects message-history order, not wall-clock completion.
    Call IDs are replaced by local aliases: provider/model-controlled IDs could
    themselves contain sensitive text. Raw IDs are used only for internal linkage.
    """
    pending = {}
    trace = []
    evidence = set()
    call_number = 0

    def add_event(tool_name, alias, ids, error):
        trace.append({
            'sequence': len(trace) + 1,
            'tool': tool_name if tool_name in SOURCE_TYPES else '<unknown>',
            'tool_call_id': alias,
            'returned_ids': ids,
            'error': error,
        })

    for message in messages:
        for part in message.parts:
            if isinstance(part, ToolCallPart):
                call_number += 1
                alias = f'call_{call_number}'
                # Duplicate pending IDs are ambiguous; never count their evidence.
                if part.tool_call_id in pending:
                    name, previous_alias = pending[part.tool_call_id]
                    add_event(name, previous_alias, [], 'duplicate_call_id')
                    pending[part.tool_call_id] = ('<ambiguous>', alias)
                else:
                    pending[part.tool_call_id] = (part.tool_name, alias)
            elif isinstance(part, (ToolReturnPart, RetryPromptPart)):
                requested = pending.pop(part.tool_call_id, None)
                if requested is None:
                    add_event(part.tool_name, None, [], 'unmatched_tool_return')
                    continue
                name, alias = requested
                if name != part.tool_name:
                    add_event(name, alias, [], 'tool_name_mismatch')
                    continue
                if name not in SOURCE_TYPES:
                    add_event(name, alias, [], 'unknown_tool')
                    continue
                if isinstance(part, RetryPromptPart):
                    add_event(name, alias, [], 'tool_retry')
                    continue
                if part.outcome != 'success':
                    add_event(name, alias, [], 'tool_retry' if part.outcome == 'retried' else 'tool_failed')
                    continue
                if isinstance(part.content, dict) and 'error' in part.content:
                    # Never copy arbitrary error text or exception payloads.
                    code = ('asset_not_found' if name == 'get_asset_details'
                            and part.content['error'] == 'asset_not_found' else 'tool_error')
                    add_event(name, alias, [], code)
                    continue
                ids = returned_ids(name, part.content)
                evidence.update(ids)
                add_event(name, alias, ids, None)
    for name, alias in pending.values():
        add_event(name, alias, [], 'missing_tool_return')
    return sorted(evidence), trace


def _citation_checks(answer, evidence_ids):
    """Check disclaimer, formatting, membership and evidence kinds, not entailment.

    As in the notebook, require one citation per retrieved kind. This conservative
    heuristic may flag answers that intentionally omit irrelevant retrieved records.
    """
    evidence = set(evidence_ids)
    issues = []
    if not answer.startswith(DISCLAIMER):
        issues.append(('missing_disclaimer', 'Begin the answer with the synthetic-training disclaimer: ' + DISCLAIMER))
    if re.search(r'\[[^\]\n]*[A-Za-z][A-Za-z0-9_]*-\d+[^\]\n]*\]\s*\(', answer):
        issues.append(('invalid_citation_format', 'Use plain bracketed source IDs, not Markdown links.'))
    cited = set(re.findall(r'\[(' + SOURCE_PATTERN + r')\]', answer))
    for bracket in re.findall(r'\[([^\[\]\n]+)\]', answer):
        # Also flag unknown prefixes, wrong case/length, and grouped source IDs.
        if re.search(r'[A-Za-z][A-Za-z0-9_]*-\d+', bracket):
            if not re.fullmatch(SOURCE_PATTERN, bracket):
                issues.append(('invalid_citation_format', 'Unsupported source-ID format/category; cite one returned ID per bracket.'))
    if cited - evidence:
        issues.append(('unretrieved_citation', 'Unretrieved citations: ' + ', '.join(sorted(cited - evidence))
                      + '. Remove them or retrieve supporting records.'))
    if evidence and not cited:
        issues.append(('missing_citation', 'Evidence was retrieved but no bracketed citations appear; cite supported findings.'))
    for _, pattern, label in SOURCE_TYPES.values():
        if any(re.fullmatch(pattern, source) for source in evidence):
            if not any(re.fullmatch(pattern, source) for source in cited & evidence):
                issues.append(('missing_citation', f'Missing valid {label} citation; cite a returned ID beside supported findings.'))
    return list(dict.fromkeys(issues))


def citation_issues(answer, evidence_ids):
    """Keep the existing human-readable citation-reporting interface."""
    return [message for _, message in _citation_checks(answer, evidence_ids)]


TECHNICAL_TOPICS = {
    'dependencies': r'\bdependenc\w*|\bbatch jobs?\b|\bscheduled jobs?\b',
    'configuration': r'\bconfigurat\w*|\bplatform\b',
    'network': r'\bconnectivity\b|\bdns\b|\bfirewall\w*|\bprotocol\w*|\bports?\b',
    'policy': r'\bpassword polic\w*|\bminimum age\b|\bcomplexity\b',
    'permissions': r'\bpermissions?\b|\baccount (?:state|restrictions?)\b',
    'web connector': r'\bselectors?\b|\bpage structure\b|\bredirect\w*|\blogin (?:field|element)\b',
    'timing': r'\brotation schedule\b|\btarget availability\b',
}


def _documentation_checks(answer, messages):
    """Conservative lexical guard for explicit technical actions, not semantics.

    Basic requests to collect/provide sanitized errors, timestamps or approved
    evidence are not technical procedures under this policy. Detected actions
    require a nearby returned article citation with matching topic vocabulary.
    This intentionally does not claim to recognize every possible procedure.
    """
    evidence, _ = collect_evidence(messages)
    docs = {}
    for message in messages:
        for part in message.parts:
            if (isinstance(part, ToolReturnPart) and part.tool_name == 'search_documentation'
                    and part.outcome == 'success' and isinstance(part.content, list)):
                for record in part.content:
                    if isinstance(record, dict) and record.get('id') in evidence and 'error' not in record:
                        docs[record['id']] = str(record.get('title', '')) + ' ' + str(record.get('content', ''))
    issues = []
    for clause in re.split(r'\n+|(?<=[.!?])\s+', answer):
        plain = re.sub(r'[*`#]', '', clause).lower()
        topics = set()
        for action in re.finditer(r'\b(?:review|check|inspect|compare|verify|examine|validate|'
                                  r'investigate|test|trace|confirm|correlate)\b', plain):
            prefix = plain[max(0, action.start() - 35):action.start()]
            if re.search(r'(?:cannot|can.t|do not|don.t|unable to|will not)\s*$', prefix):
                continue
            target = plain[action.end():action.end() + 120]
            topics.update(name for name, pattern in TECHNICAL_TOPICS.items() if re.search(pattern, target))
        cited = set(re.findall(r'\[((?:ONB|ROT|WEB)-\d{3})\]', clause))
        for topic in sorted(topics):
            if not any(source in docs and re.search(TECHNICAL_TOPICS[topic], docs[source], re.I)
                       for source in cited):
                issues.append(('unsupported_documentation_guidance',
                              f'Technical {topic} guidance needs a nearby returned documentation '
                              'citation with matching topic evidence. Retrieve documentation or omit '
                              'the procedure and explain that documentation evidence is unavailable.'))
    return list(dict.fromkeys(issues))


def documentation_issues(answer, messages):
    """Keep the existing human-readable documentation-reporting interface."""
    return [message for _, message in _documentation_checks(answer, messages)]


def answer_validation_checks(answer, messages):
    """Produce (fixed code, existing message) pairs directly from failed checks."""
    evidence, _ = collect_evidence(messages)
    return _citation_checks(answer, evidence) + _documentation_checks(answer, messages)


def summarize_result(result):
    """Summarize an actual AgentRunResult without exposing its raw messages."""
    evidence_ids, trace = collect_evidence(result.all_messages())
    issues = citation_issues(result.output, evidence_ids)
    usage = result.usage
    return {
        'answer': result.output,
        'evidence_ids': evidence_ids,
        'trace': trace,
        'citation_issues': issues,
        'citation_validation_passed': not issues,
        'usage': {
            'model_requests': usage.requests,
            'tool_calls': usage.tool_calls,
            'input_tokens': usage.input_tokens,
            'output_tokens': usage.output_tokens,
            'total_tokens': usage.total_tokens,
        },
    }
