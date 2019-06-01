from examples.example_1 import add, LEARNING_RATE, DECAY
from examples.example_2 import FACTOR

if __name__ == '__main__':
    sum_ = LEARNING_RATE + DECAY
    print('Sum of {} and {} is {}'.format(LEARNING_RATE, DECAY, sum_))
    print('Factor is {}'.format(FACTOR))
    print('The sum of the above is', add(sum_, FACTOR))
