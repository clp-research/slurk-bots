class Wordle:
    def __init__(self, word):
        self.word = word
        self.correct = [" " for i in range(len(word))]
        self.wrong_position = set()
        self.not_in_word = set()

    @property
    def remaining(self):
        return set(self.word) - set(self.correct)

    def __len__(self):
        return len(self.word)

    def game_over(self):
        if self.word == "".join(self.correct):
            return True
        return False

    def guess(self, guess):
        # first pass, we look for correct letters
        for i, letter in enumerate(guess):
            if letter == self.word[i]:
                self.correct[i] = letter

        for i, letter in enumerate(guess):
            if letter in self.remaining:
                self.wrong_position.add(letter)
            
            else:
                if letter not in self.word:
                    self.not_in_word.add(letter)

    def stats(self):
        print(f"Right position: {self.correct}")
        print(f"Wrong position: {self.wrong_position}")
        print(f"Useless letters: {self.not_in_word}")


word = Wordle("ropes")
t = 5
lost = True

while t > 0:
    guess = input("Enter your guess:\n> ")

    if len(guess) != len(word):
        print(f"your guess must be {len(word)} letters long")
    else:
        word.guess(guess)
        if word.game_over():
            print("\nYOU WIN")
            lost = False
            break
        t -= 1     
        print(f"\nRemaining Guesses: {t}") 
        word.stats()
if lost:
    print("\nGAME OVER")
