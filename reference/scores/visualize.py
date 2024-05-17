
import matplotlib.pyplot as plt
import os
import json
import numpy as np

from scores.calculate_reference_metrics import (
    compute_model_average_scores,
    compute_average_scores,
)


def create_plot(model_results, human_resutls, y_label, model_name, lim, dir="plots"):
    mean_scores = {model_name: [], "humans": []}
    categories = []
    for key, value in model_results.items():
        categories.append(key)
        mean_scores[model_name].append(round(value))
        mean_scores["humans"].append(round(human_resutls[key]))
    x = np.arange(len(categories))  # the label locations
    width = 0.25  # the width of the bars
    multiplier = 1

    fig, ax = plt.subplots(layout="constrained", figsize=(10, 6))

    for attribute, measurement in mean_scores.items():
        offset = width * multiplier
        rects = ax.bar(x + offset, measurement, width, label=attribute)
        ax.bar_label(rects, padding=3)
        multiplier += 1

    # Add some text for labels, title and custom x-axis tick labels, etc.
    ax.set_ylabel(y_label)
    # ax.set_title('Generated Expression Length per Grid Type')
    ax.set_xticks(x + width, categories)
    ax.legend(loc="upper left", ncols=3)
    ax.set_ylim(0, lim)

    # plt.show()
    if not os.path.exists(dir):
        os.makedirs(dir)
    plt.savefig(f"{dir}/{y_label}_reference.png")

    return "plot saved in f'{y_label}_reference.png"



if __name__ == "__main__":
    with open(os.path.join("human_scores.json"), "r") as f:
        human_scores = json.load(f)

    with open(os.path.join("model_scores.json"), "r") as f:
        model_scores = json.load(f)

    model_length = compute_model_average_scores(
        model_scores, "Average Generated Expression Length"
    )
    human_length = compute_average_scores(
        human_scores, "Average Generated Expression Length"
    )
    create_plot(model_length, human_length, "Length", "gpt-4-0613", 250)

    model_tokens = compute_model_average_scores(
        model_scores, "Average Generated Expression Number of Tokens"
    )
    human_tokens = compute_average_scores(
        human_scores, "Average Generated Expression Number of Tokens"
    )
    create_plot(model_tokens, human_tokens, "Number of Tokens", "gpt-4-0613", 60)
