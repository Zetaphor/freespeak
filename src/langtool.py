# This example has minimal configuration and lets Language Tool do the work to
# make it look right. (I am not at all affiliated with Language tool, I just
# found it useful to work with nerd-dictation.)
#
# Language Tool is a free service (or local server for the paranoid!) for low
# request volume and I have added it to my nerd-dictation configuration to
# correct and add punctuation where necessary.  I have found that it makes far,
# far less manual editing in the result of the spoken text:
#   https://languagetool.org/
#
# Here is a simple example:
#
# Raw spoken input:
#    can we go to costa rica in june question mark it is for my son's twelfth
#    birthday and i hope we have a lot of fun period
#
# This is the result without editing:
#    Can we go to Costa Rica in June? It is for my son's twelfth birthday and
#    I hope we have a lot of fun.
#
# For which the following rules were applied:
#    Rule: UPPERCASE_SENTENCE_START
#    Rule: EN_SPECIFIC_CASE
#    Rule: MORFOLOGIK_RULE_EN_US
#    Rule: UPPERCASE_SENTENCE_START
#    Rule: I_LOWERCASE
#
# nerd-dictation was invoked as follows:
#    ./nerd-dictation begin --config ./examples/language_tool/nerd-dictation.py
#
# I used the Vosk model vosk-model-en-us-0.22-lgraph, but it probably does not
# matter which model you use.

import re
import requests
from pprint import pprint

PUNCTUATION = {
    "comma": ",",
    "period": ".",
    "exclamation mark": "!",
    "question mark": "?",
}

# Change this if necessary:
language = "en-US"


def langtool_process(text):
    print("<<<< " + text)

    # Fix up punctuation first because the grammar parser works better:
    for match, replacement in PUNCTUATION.items():
        # Use case-insensitive matching (i)
        # Capture whitespace BEFORE the optional single space (\s*) - group 1
        # Capture an optional single space immediately before the match (\s?) - group 2
        # Match the punctuation word (escaped)
        # Use a positive lookahead (?=...) for context.
        # Replace with group 1 + punctuation symbol. This removes the single
        # space captured by group 2 if it existed.
        pattern = rf"(?i)(\s*)(\s?){re.escape(match)}(?=\s+|[.,?!]|$)"
        text = re.sub(pattern, lambda x: x.group(1) + replacement, text)

    # Iterate langtool while it finds additional changes (or 3 tries):
    tries = 3
    while True:
        new_text = langtool(text, language)
        if new_text == text or not tries:
            break
        else:
            text = new_text

        tries -= 1

    print(">>>> " + new_text)

    return new_text


# Simple API function.  Documentation:
#    https://languagetool.org/http-api/swagger-ui/#!/default/post_check
def langtool(text, language):
    try:
        r = requests.post(
            "http://localhost:8010/v2/check",
            data={
                "text": text,
                "language": language,
                "enabledOnly": "false",
                "level": "default",
                #'level': 'picky', # or be more picky
            },
            timeout=5 # Add a timeout
        )
        r.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
    except requests.exceptions.RequestException as e:
        print(f"\n======== Langtool request failed: {e}")
        # Return original text if LT request fails
        return text

    try:
        data = r.json()
    except requests.exceptions.JSONDecodeError:
        print(f"\n======== Langtool response is not valid JSON: {r.text}")
        # Return original text if response is not JSON
        return text


    if "matches" not in data:
        print(f"\n======== Langtool response missing 'matches' key: {data}")
        return text # Return original text if response format is unexpected

    # Sort matches by offset to apply them correctly even if lengths change
    matches = sorted(data["matches"], key=lambda x: x["offset"])

    # Use a list to build the new text piece by piece to handle offset changes
    new_text_parts = []
    last_index = 0

    for m in matches:
        # --- Using the list building approach avoids offset issues ---
        o = m["offset"]
        n = m["length"]

        # Add the text segment before the current match
        # Ensure indices are valid
        if o < last_index:
             print(f"\n======== Langtool encountered overlapping match or sorting issue. Skipping match: {m}")
             continue # Skip this match if offsets seem wrong
        new_text_parts.append(text[last_index:o])

        print("  Rule: " + m["rule"]["id"])
        if m["rule"]["id"] in ["TOO_LONG_SENTENCE"]:
            # Skip rules from Language Tool that you don't want:
            print("============== langtool skipping ID: " + m["rule"]["id"])
            # Add the original matched text back if skipping
            new_text_parts.append(text[o : o + n])

        elif len(m["replacements"]) >= 1:
            # Try the first replacement
            new_text_parts.append(m["replacements"][0]["value"])

        elif n > 0:
            # No replacement suggestions, but a length is provided so point out
            # the unexpected content with square brackets:
            # Note: This might not be desirable behavior, consider removing or changing.
            new_text_parts.append("[" + text[o : o + n] + "]")

        else:
            # If we get here this is probably an unhandled case:
            print("\n\n======== langtool no replacement and zero length? Match:")
            # Limit the "replacements" list to prevent huge debug:
            m["replacements"] = m["replacements"][0:3]
            pprint(m)
            # Add the original text back in this unexpected case
            new_text_parts.append(text[o : o + n])

        # Update the index for the next segment
        last_index = o + n

    # Add any remaining text after the last match
    new_text_parts.append(text[last_index:])

    # Join the parts to form the final text
    text = "".join(new_text_parts)

    return text