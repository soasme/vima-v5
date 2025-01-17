import csv
import json
import sys
import random
data = json.load(sys.stdin)

ANSWER_HANDLES = {1: 'A', 2: 'B', 3: 'C'}
CONGRATS = [
    'Congratulations!',
    'Well done!',
    'You are amazing!',
    'You are a genius!',
    'You are a star!',
    'You are a champion!',
    'You are a winner!',
    'You are a superhero!',
    'You are a legend!',
    'Great job!',
    'Excellent!',
    'Fantastic!',
    'Brilliant!',
    'Awesome!',
    'Outstanding!',
    'Impressive!',
    'Incredible!',
    'Unbelievable!',
    'Remarkable!',
    'Extraordinary!',
    "What a performance!",
    "What an achievement!",
    "What a success!",
    "What a victory!",
    "What a triumph!",
    "What a breakthrough!",
    "What a milestone!",
    "Wow, you're on fire!",
    "Wow, you're on a roll!",
    "Wow, you're on a winning streak!",
    "Wow, you're on a winning spree!",
    "Wow, you're on a winning run!",
]


def make_bulk_csv():
    rows = [
        ['Question 1', 'Question 2', 'Question 3', 'Answer', 'Correct Answer', 'Explanation', 'Explanation Source', 'Fun Fact']
    ]
    for elem in data:
        row = [
            elem['Questions'][0],
            elem['Questions'][1],
            elem['Questions'][2],
            elem['Answer'],
            ANSWER_HANDLES[elem['Questions'].index(elem['Answer']) + 1],
            elem['Explain'].split(', ')[0],
            elem['Explain'].split(', ')[1],
            elem['Fun Fact']
        ]
        rows.append(row)
    writer = csv.writer(sys.stdout)
    writer.writerows(rows)

def make_script():
    res = []
    for idx, elem in enumerate(data):
        answer = ANSWER_HANDLES[elem['Questions'].index(elem['Answer']) + 1]
        fusion1 = elem['Explain'].split(', ')[0]
        fusion2 = elem['Explain'].split(', ')[1]
        congrats = random.choice(CONGRATS)
        line = []
        line.append(f'LEVEL {idx + 1}. ')
        line.append('... ' )
        line.append('Guess who I am?')
        line.append('... ' )
        line.append(f'A. {elem["Questions"][0]}.')
        line.append('... ' )
        line.append(f'B. {elem["Questions"][1]}.')
        line.append('... ' )
        line.append(f'C. {elem["Questions"][2]}.')
        line.append('... ' )
        line.append(congrats)
        line.append(f'The answer is {answer}, {elem["Answer"]}. ')
        line.append(f"It's the fusion of {fusion1} and {fusion2}. ")
        res.append(' '.join(line))

    print('\n'.join(res))

if __name__ == '__main__':
    make_script()
