import pandas as pd


def main():
    # import the pairs file
    df1 = pd.read_csv("../data/image_data.tsv", sep="\t", header=None)
    df1.columns = ["term", "image_path"]

    # import the existing wordslist
    df2 = pd.read_csv("../data/wordlist.txt", sep=" ", header=None)
    df2.columns = ["term"]

    # update the existing wordslist
    df3 = pd.concat([df1["term"], df2["term"]]).drop_duplicates().reset_index(drop=True)

    # sort it alphabetically and replace it
    df3 = df3.sort_values()
    df3.to_csv("../data/wordlist.txt", sep="\n", index=False, header=False)

    print("Wordlist updated!")
    print(
        "The wordlist has gained "
        + str(len(df3.index) - len(df2.index))
        + " new entries."
    )


if __name__ == "__main__":
    main()
