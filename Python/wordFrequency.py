import re
from collections import Counter

def extract_messages(input_file):
    messages = []
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    message_pattern = re.compile(r"^\[\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2} [AP]M\] .+")
    current_message = []
    in_chat_section = False

    for line in lines:
        line = line.strip()
        if "Guild:" in line or "Channel:" in line or line.startswith("="):
            continue  # Skip header lines

        if message_pattern.match(line):
            if current_message:
                messages.append(" ".join(current_message))
                current_message = []

            # Strip out timestamp and username
            parts = line.split("]", 1)
            if len(parts) > 1:
                message_part = parts[1].strip().split(" ", 1)
                if len(message_part) > 1:
                    content = message_part[1].strip()
                    current_message.append(content)
        else:
            if line:
                current_message.append(line)

    if current_message:
        messages.append(" ".join(current_message))

    return messages

def count_words(messages):
    word_counter = Counter()
    for msg in messages:
        # Keep contractions like "don't"
        words = re.findall(r"\b[\w']+\b", msg.lower())
        word_counter.update(words)
    return word_counter

def save_word_frequencies(word_counter, output_file):
    sorted_words = word_counter.most_common()
    with open(output_file, 'w', encoding='utf-8') as f:
        for word, count in sorted_words:
            f.write(f"{word}: {count}\n")

def main():
    input_file = "chat_log.txt"
    output_file = "word_frequencies.txt"

    messages = extract_messages(input_file)
    print(f"Found {len(messages)} messages.")

    word_counts = count_words(messages)
    save_word_frequencies(word_counts, output_file)
    print(f"Saved word frequencies to: {output_file}")

if __name__ == "__main__":
    main()
