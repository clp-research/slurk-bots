import matplotlib.pyplot as plt
import os

from scores.vocabulary import count_word_freqs


def plot_most_common_words(word_frequencies, file_name, dir="plots"):
    sorted_word_frequencies = sorted(
        word_frequencies.items(), key=lambda x: x[1], reverse=False
    )
    words = [item[0] for item in sorted_word_frequencies]
    frequencies = [item[1] for item in sorted_word_frequencies]

    plt.figure(figsize=(10, 6))
    plt.barh(range(len(words)), frequencies, color="skyblue")
    plt.xlabel("Frequency")
    plt.ylabel("Words")
    plt.yticks(range(len(words)), words)  # Use words as y-tick labels

    plt.xlim(0, 38)

    plt.tight_layout()  # Adjust layout to prevent clipping of labels
    # plt.show()
    if not os.path.exists(dir):
        os.makedirs(dir)
    plt.savefig(f"{dir}/{file_name}")


if __name__ == "__main__":
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    model_word_freqs = count_word_freqs("model_expressions.json")
    human_word_freqs = count_word_freqs("human_expressions.json")
    plot_most_common_words(
        model_word_freqs, "model_words_frequencies.png", f"{ROOT}/scores/plots"
    )
    plot_most_common_words(
        human_word_freqs, "human_words_frequencies.png", f"{ROOT}/scores/plots"
    )
