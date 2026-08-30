import spacy
from spacy.matcher import Matcher

nlp = spacy.load("en_core_web_sm")
matcher = Matcher(nlp.vocab)

# Define patterns to look for numbers/words followed by time units and "notice"
patterns = [
    [{"LIKE_NUM": True}, {"LOWER": {"IN": ["day", "days", "week", "weeks", "month", "months"]}},{"LOWER": "notice"}],
    [{"LOWER":{"IN":["immediate","immediately"]}}, {"LOWER": {"IN": ["joiner", "joiners", "joining"]}}] 
]
matcher.add("NOTICE_PERIOD", patterns)

def extract_notice(text):
    doc = nlp(text)
    matches = matcher(doc)
    return [doc[start:end].text for match_id, start, end in matches]

job_desc = "The candidate must have a 2 months notice period. Joining should be quick."
print(extract_notice(job_desc))
# Output: ['2 months notice']