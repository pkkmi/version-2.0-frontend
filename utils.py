import random
import re
from config import pricing_plans

# Helper function to humanize text
def humanize_text(text, user_type):
    # Simple humanization algorithm
    word_count = len(text.split())
    user_limit = pricing_plans[user_type]["word_limit"]

    if word_count > user_limit:
        # Truncate text if beyond word limit
        words = text.split()
        text = " ".join(words[:user_limit])
        message = f"Text truncated to {user_limit} words (your plan limit). Upgrade for more!"
    else:
        message = f"Used {word_count} of {user_limit} available words"

    # Simple humanization rules
    humanized = text

    # Add some contractions
    humanized = humanized.replace("I am", "I'm")
    humanized = humanized.replace("do not", "don't")
    humanized = humanized.replace("cannot", "can't")
    humanized = humanized.replace("will not", "won't")

    # Add some filler words at random positions
    filler_words = ["actually", "basically", "honestly", "like", "you know", "I mean", "well", "sort of", "kind of"]
    sentences = re.split(r'(?<=[.!?])\s+', humanized)

    for i in range(len(sentences)):
        if random.random() < 0.3:  # 30% chance to add a filler word
            filler = random.choice(filler_words)
            words = sentences[i].split()
            if len(words) > 3:
                insert_pos = random.randint(1, len(words) - 1)
                words.insert(insert_pos, filler)
                sentences[i] = " ".join(words)

    humanized = " ".join(sentences)

    # Occasionally change punctuation
    if random.random() < 0.2:
        humanized = humanized.replace(".", "...")

    # Sometimes make a simple grammatical "mistake"
    if random.random() < 0.15:
        humanized = humanized.replace(" is ", " are ")

    # Add some variability in sentence structure
    humanized = humanized.replace("Additionally", "Also")
    humanized = humanized.replace("Furthermore", "Plus")
    humanized = humanized.replace("However", "But")

    return humanized, message


# AI detector function
def detect_ai_content(text):
    # This is a simplified AI detection algorithm for demo purposes
    # In a real application, this would use more sophisticated methods

    # Detection heuristics - looking for patterns common in AI text
    ai_indicators = [
        "furthermore,", "additionally,", "moreover,", "thus,", "therefore,",
        "consequently,", "hence,", "as a result,", "in conclusion,",
        "to summarize,", "in summary,"
    ]

    # Count indicators
    indicator_count = sum(text.lower().count(indicator) for indicator in ai_indicators)

    # Check for repetitive phrases
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentence_starts = [sentence.split()[0].lower() if sentence.split() else "" for sentence in sentences]
    repeated_starts = len(sentence_starts) - len(set(sentence_starts))

    # Calculate uniformity of sentence length (standard deviation as percentage of mean)
    sentence_lengths = [len(sentence) for sentence in sentences if sentence]
    if sentence_lengths:
        mean_length = sum(sentence_lengths) / len(sentence_lengths)
        variance = sum((length - mean_length) ** 2 for length in sentence_lengths) / len(sentence_lengths)
        std_dev = variance ** 0.5
        length_uniformity = std_dev / mean_length if mean_length > 0 else 0
    else:
        length_uniformity = 0

    # Calculate AI likelihood score (0-100)
    base_score = min(100, (indicator_count * 10) + (repeated_starts * 5) + (100 - length_uniformity * 100))
    randomizer = random.uniform(0.85, 1.15)  # Add some randomness
    ai_score = min(100, max(0, base_score * randomizer))

    # Results
    result = {
        "ai_score": round(ai_score, 1),
        "human_score": round(100 - ai_score, 1),
        "analysis": {
            "formal_language": min(100, indicator_count * 15),
            "repetitive_patterns": min(100, repeated_starts * 20),
            "sentence_uniformity": min(100, (1 - length_uniformity) * 100)
        }
    }

    return result
