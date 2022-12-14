#!/usr/bin/env python3
#-*- coding: utf-8 -*-

# Very simple tetris implementation
#
# Control keys:
#       Down - Drop stone faster
# Left/Right - Move stone
#         Up - Rotate Stone clockwise
#     Escape - Quit game
#          P - Pause game
#     Return - Instant drop
#
# Have fun!

# NOTE: If you're looking for the old python2 version, see
#       <https://gist.github.com/silvasur/565419/45a3ded61b993d1dd195a8a8688e7dc196b08de8>

# Copyright (c) 2010 "Laria Carolin Chabowski"<me@laria.me>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import random
import pygame, sys
import time
from copy import deepcopy
import pandas as pd

# The configuration
cell_size = 30
cols =      10
rows =      22
maxfps =    30

colors = [
(0,   0,   0  ),
(148, 0,  211),
(50, 205, 50),
(255, 0, 0),
(0, 0, 255 ),
(255,  165, 0 ),
(3, 228, 248 ),
(255, 255, 0 ),
(35,  35,  35) # Helper color for background grid
]

# Define the shapes of the single parts
tetris_shapes = [
    [[0, 1, 0],
     [1, 1, 1]],

    [[0, 2, 2],
     [2, 2, 0]],

    [[3, 3, 0],
     [0, 3, 3]],

    [[4, 0, 0],
     [4, 4, 4]],

    [[0, 0, 5],
     [5, 5, 5]],

    [[6, 6, 6, 6]],

    [[7, 7],
     [7, 7]]
]

def rotate_counter_clockwise(shape):
    return [
        [ shape[y][x] for y in range(len(shape))]
        for x in range(len(shape[0])-1 , -1, -1)
    ]

def rotate_clockwise(shape):
    return [
        [ shape[y][x] for y in range(len(shape)-1, -1, -1)]
        for x in range(0, len(shape[0]))
    ]

def rotate_reverse(shape):
    shape[0], shape[-1] = shape[-1], shape[0]

    for x in range(len(shape)):
        shape[x] = shape[x][-1::-1]

    return shape

def check_collision(board, shape, offset):
    off_x, off_y = offset
    for cy, row in enumerate(shape):
        for cx, cell in enumerate(row):
            try:
                if cell and board[ cy + off_y ][ cx + off_x ]:
                    return True
            except IndexError:
                return True
    return False

def remove_row(board, row):
    del board[row]
    return [[0 for i in range(cols)]] + board

def join_matrixes(mat1, mat2, mat2_off):
    mat1 = list(mat1)
    off_x, off_y = mat2_off
    #print(off_y)
    for cy, row in enumerate(mat2):
        for cx, val in enumerate(row):
            mat1[cy+off_y-1 ][cx+off_x] += val
    return mat1

def new_board():
    board = [
        [ 0 for x in range(cols) ]
        for y in range(rows)
    ]
    board += [[ 1 for x in range(cols)]]
    return board

class tetris_agent:
    def __init__(self, clear_rate, leveler):
        self.space_below_rate = -5
        self.clear_rate = clear_rate
        self.approaching_lc = 10
        self.block_look_ahead = 1
        self.leveler = leveler

        self.pos_cur_moves = []
        self.pos_hold_moves = []

        self.board = None
        self.board_copy = None
        self.stone = None
        self.hold_stone = None
        self.cols = None
        self.stone_x = None
        self.stone_y = None

        self.pos_move = None

    def set_values(self, board, cur_stone, hold_stone, cols):
        #print(cur_stone)
        #print(hold_stone)
        self.board = deepcopy(board)
        self.board_copy = deepcopy(board)
        self.stone = cur_stone
        self.hold_stone = hold_stone
        self.cols = cols
        self.stone_x = self.cols - len(self.stone[0])
        self.stone_y = 0

        self.pos_cur_moves = []
        self.pos_hold_moves = []

        self.pos_move = None

    def solve(self, board, cur_stone, hold_stone, cols):
        #print("solving")
        self.set_values(board, cur_stone, hold_stone, cols)
        #print("set values done")
        self.look_ahead()
        #print("look ahead done")
        self.board_rate()
        #print("board_rate done")
        return self.best_backtrack()

    def look_ahead(self):

        self.pos_cur_moves = []
        self.pos_hold_moves = []

        self.cur_score = []
        self.hold_score = []

        for _ in range(4):
            while self.stone_x > 0:
                self.insta_drop()
                self.pos_cur_moves.append(self.pos_move)
                self.move(-1)
                if len(self.pos_cur_moves) > 1:
                    if(self.pos_cur_moves[-1] == self.pos_cur_moves[-2]):
                        break
            #print("rotating")
            #print(self.pos_cur_moves)
            #print(self.board)
            #print(self.board_copy)
            self.insta_drop()
            self.pos_cur_moves.append(self.pos_move)
            self.rotate_stone_clockwise()
            self.stone_x = self.cols - len(self.stone[0])

        if sum(self.hold_stone[0]) > 0:
            self.switch_hold()
            for _ in range(4):
                while self.stone_x > 0:
                    self.insta_drop()
                    self.pos_hold_moves.append(self.pos_move)
                    self.move(-1)
                    if len(self.pos_hold_moves) > 1:
                        if (self.pos_hold_moves[-1] == self.pos_hold_moves[-2]):
                            break
                self.insta_drop()
                self.pos_hold_moves.append(self.pos_move)
                self.rotate_stone_clockwise()
                self.stone_x = self.cols - len(self.stone[0])
            self.switch_hold()

    def drop(self):
        self.stone_y += 1
        if check_collision(self.board,
                           self.stone,
                           (self.stone_x, self.stone_y)):
            self.board = join_matrixes(
              self.board,
              self.stone,
              (self.stone_x, self.stone_y))

            self.pos_move = self.board
            self.board = deepcopy(self.board_copy)
            #print(self.pos_move)
            self.stone_y = 0
            return True
        return False

    def insta_drop(self):
        while(self.drop() == False):
            pass

    def move(self, delta_x):
        new_x = self.stone_x + delta_x
        if new_x < 0:
            new_x = 0
        if new_x > self.cols - len(self.stone[0]):
            new_x = self.cols - len(self.stone[0])
        if not check_collision(self.board,
                               self.stone,
                               (new_x, self.stone_y)):
            self.stone_x = new_x

    def rotate_stone_clockwise(self):
        new_stone = rotate_clockwise(self.stone)
        if not check_collision(self.board,
                               new_stone,
                               (self.stone_x, self.stone_y)):
            self.stone = new_stone

    def switch_hold(self):
        self.stone, self.hold_stone = self.hold_stone, tetris_shapes[max(self.stone[0])-1]
        self.stone_x = self.cols - len(self.stone[0])

    def board_rate(self):
        for b in self.pos_cur_moves:
            remove_index = []
            score = 0
            highest = 0
            found_highest = False
            for row in range(len(b)):
                if sum(b[row]) > 0:
                    #print("true")
                    if not(0 in b[row]):
                        score += self.clear_rate
                    else:
                        if not found_highest:
                            found_highest = True
                            highest = len(b) - row
                            #print("highest is " + str(highest))
                        for index in range(self.cols):
                            if index not in remove_index and b[row][index]>0:
                                remove_index.append(index)
                                #print(b)

                                for index_below in range(row+1, len(b)):
                                    if b[index_below][index] == 0:
                                        score += self.space_below_rate
                                        #print(row+1, index)
                                        #print(score)
            score -= highest * self.leveler
            self.cur_score.append(score)
            #print(self.cur_score)

        for b in self.pos_hold_moves:
            remove_index = []
            score = 0
            highest = 0
            found_highest = False
            for row in range(len(b)):
                if sum(b[row]) > 0:
                    if not (0 in b[row]):
                        score += self.clear_rate
                    else:
                        if not found_highest:
                            found_highest = True
                            highest = len(b) - row
                            #print("highest is " + str(highest))
                        for index in range(self.cols):
                            if index not in remove_index and b[row][index]>0:
                                remove_index.append(index)

                                for index_below in range(row + 1, len(b)):
                                    if b[index_below][index] == 0:
                                        score += self.space_below_rate

            score -= highest * self.leveler
            self.hold_score.append(score)

    def best_backtrack(self):
        cur_move1 = self.cols - len(self.stone[0]) + 1
        cur_move2 = self.cols - len(self.stone) + 1
        self.switch_hold()
        hold_move1 = self.cols - len(self.stone[0]) + 1
        hold_move2 = self.cols - len(self.stone) + 1

        self.switch_hold()

        index_high = 0
        hold_index_high = 0

        if random.randint(0,1) == 0:
            cur_high = max(self.cur_score)
            index_high = self.cur_score.index(cur_high)
            if len(self.hold_score)>0:
                hold_high = max(self.hold_score)
                hold_index_high = self.hold_score.index(hold_high)
            else:
                hold_high = -1000
        else:
            self.cur_score.reverse()
            self.hold_score.reverse()
            cur_high = max(self.cur_score)
            index_high = (len(self.cur_score)-1) - self.cur_score.index(cur_high)
            if len(self.hold_score) > 0:
                hold_high = max(self.hold_score)
                hold_index_high = (len(self.hold_score)-1) - self.hold_score.index(hold_high)
            else:
                hold_high = -1000
            self.cur_score.reverse()
            self.hold_score.reverse()

        do_switch = 0
        #print(self.cur_score)
        #print(self.hold_score)

        #print(cur_high, hold_high)

        if cur_high >= hold_high:
            if 0 <= index_high < cur_move1:
                rotation_count = 0
                stone_length = len(self.stone[0])
            elif cur_move1 <= index_high < cur_move1 + cur_move2:
                rotation_count = 1
                index_high = index_high - cur_move1
                stone_length = len(self.stone)
            elif cur_move1 + cur_move2 <= index_high < cur_move1*2 + cur_move2:
                rotation_count =2
                index_high = index_high - (cur_move1 + cur_move2)
                stone_length = len(self.stone[0])
            else:
                rotation_count = 3
                index_high = index_high - (cur_move1*2 + cur_move2)
                stone_length = len(self.stone)

            stone_x = cols - stone_length - index_high
            if (stone_length < 3) and not sum(self.stone[0]) == 14:
                move_count = stone_x - int(cols / 2 - stone_length / 2) + 1
            else:
                move_count = stone_x - int(cols / 2 - stone_length / 2)

            #print(do_switch, rotation_count, move_count)
            #print("end")
            return do_switch, rotation_count, move_count

        else:
            self.switch_hold()
            if 0 <= hold_index_high < hold_move1:
                rotation_count = 0
                stone_length = len(self.stone[0])
            elif hold_move1 <= hold_index_high < hold_move1 + hold_move2:
                rotation_count = 1
                hold_index_high = hold_index_high - hold_move1
                stone_length = len(self.stone)
            elif hold_move1 + cur_move2 <= hold_index_high < hold_move1 * 2 + hold_move2:
                rotation_count = 2
                hold_index_high = hold_index_high - (hold_move1 + hold_move2)
                stone_length = len(self.stone[0])
            else:
                rotation_count = 3
                hold_index_high = hold_index_high - (hold_move1 * 2 + hold_move2)
                stone_length = len(self.stone)

            stone_x = cols - stone_length - hold_index_high

            if(stone_length < 3) and not sum(self.stone[0]) == 14:
                move_count = stone_x - int(cols / 2 - stone_length / 2) + 1
            else:
                move_count = stone_x - int(cols / 2 - stone_length / 2)

            do_switch = 1

            #print(do_switch, rotation_count, move_count)
            #print("end")
            return do_switch, rotation_count, move_count

class TetrisApp(object):
    def __init__(self, clear_score, leveler):
        self.bot = tetris_agent(clear_score, leveler)
        self.clear_score = clear_score
        self.leveler = leveler
        pygame.init()
        pygame.key.set_repeat(250,25)
        self.width = cell_size*(cols+6)
        self.height = cell_size*rows
        self.rlim = cell_size*cols
        self.bground_grid = [[ 8 if x%2==y%2 else 0 for x in range(cols)] for y in range(rows)]

        self.default_font =  pygame.font.Font(
            pygame.font.get_default_font(), 12)

        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.event.set_blocked(pygame.MOUSEMOTION) # We do not need
                                                     # mouse movement
                                                     # events, so we
                                                     # block them.
        self.dont_burn_my_cpu = pygame.time.Clock()

    def generate_bag(self):
        if len(self.bag) < 7:
            self.bag += random.sample(tetris_shapes, len(tetris_shapes)) + random.sample(tetris_shapes, len(tetris_shapes))


    def new_stone(self):
        self.generate_bag()
        self.stone = self.next_stone[:]
        self.next_stone = self.bag.pop(0)
        self.stone_x = int(cols / 2 - len(self.stone[0])/2)
        self.stone_y = 0

        if check_collision(self.board,
                           self.stone,
                           (self.stone_x, self.stone_y)) or self.lines >= 40:
            self.timer = time.time() - self.timer
            self.gameover = True

    def init_game(self):
        self.board = new_board()
        self.lines = 0
        self.bag = []
        self.bag += random.sample(tetris_shapes, len(tetris_shapes)) + random.sample(tetris_shapes, len(tetris_shapes))
        self.next_stone = self.bag.pop(0)
        self.new_stone()
        self.level = 1
        self.score = 0
        self.hold_stone = [[0,0,0],[0,0,0]]
        self.switched = False
        self.timer = time.time()
        #self.switch_hold()
        self.debugger = 0
        self.blocks = 0
        self.gameover = False
        self.paused = False
        self.rec_depth = 0
        pygame.time.set_timer(pygame.USEREVENT+1, 1000)
        return self.perform_bot()

    def perform_bot(self):
        if sum(self.hold_stone[0]) == 0:
            hold = self.next_stone
        else:
            hold = self.hold_stone
        do_switch, rotation_count, move_count = self.bot.solve(list(self.board),self.stone,hold,cols)
        if do_switch:
            self.switch_hold()
        for _ in range(rotation_count):
            self.rotate_stone_clockwise()
        if move_count < 0:
            for _ in range(abs(move_count)):
                self.move(-1)
        else:
            for _ in range(move_count):
                self.move(1)
        self.display()
        return self.insta_drop()

    def disp_msg(self, msg, topleft):
        x,y = topleft
        for line in msg.splitlines():
            self.screen.blit(
                self.default_font.render(
                    line,
                    False,
                    (255,255,255),
                    (0,0,0)),
                (x,y))
            y+=14

    def center_msg(self, msg):
        for i, line in enumerate(msg.splitlines()):
            msg_image =  self.default_font.render(line, False,
                (255,255,255), (0,0,0))

            msgim_center_x, msgim_center_y = msg_image.get_size()
            msgim_center_x //= 2
            msgim_center_y //= 2

            self.screen.blit(msg_image, (
              self.width // 2-msgim_center_x,
              self.height // 2-msgim_center_y+i*22))

    def draw_matrix(self, matrix, offset):
        off_x, off_y  = offset
        for y, row in enumerate(matrix):
            for x, val in enumerate(row):
                if val:
                    pygame.draw.rect(
                        self.screen,
                        colors[val],
                        pygame.Rect(
                            (off_x+x) *
                              cell_size,
                            (off_y+y) *
                              cell_size,
                            cell_size,
                            cell_size),0)

    def add_cl_lines(self, n):
        linescores = [0, 40, 100, 300, 1200]
        self.lines += n
        self.score += linescores[n] * self.level
        if self.lines >= self.level*6:
            self.level += 1
            newdelay = 1000-50*(self.level-1)
            newdelay = 100 if newdelay < 100 else newdelay
            pygame.time.set_timer(pygame.USEREVENT+1, newdelay)

    def move(self, delta_x):
        if not self.gameover and not self.paused:
            new_x = self.stone_x + delta_x
            if new_x < 0:
                new_x = 0
            if new_x > cols - len(self.stone[0]):
                new_x = cols - len(self.stone[0])
            if not check_collision(self.board,
                                   self.stone,
                                   (new_x, self.stone_y)):
                self.stone_x = new_x
            else:
                #print("COLLISION!!!")
                pass
    def quit(self):
        self.center_msg("Exiting...")
        pygame.display.update()
        sys.exit()

    def drop(self, manual):
        if not self.gameover and not self.paused:
            self.score += 1 if manual else 0
            self.stone_y += 1
            if check_collision(self.board,
                               self.stone,
                               (self.stone_x, self.stone_y)):
                self.board = join_matrixes(
                  self.board,
                  self.stone,
                  (self.stone_x, self.stone_y))
                #(self.stone_y)
                self.new_stone()
                self.switched = False
                cleared_rows = 0
                while True:
                    for i, row in enumerate(self.board[:-1]):
                        if 0 not in row:
                            self.board = remove_row(
                              self.board, i)
                            cleared_rows += 1
                            break
                    else:
                        break
                self.add_cl_lines(cleared_rows)
                return True
        return False

    def insta_drop(self):
        #print(self.stone_x)
        self.blocks += 1
        if not self.gameover and not self.paused:
            while(not self.drop(True)):
                pass
        if not self.gameover and not self.paused and self.debugger < 1000:
            self.debugger += 1
            self.rec_depth += 1
            self.perform_bot()
        self.rec_depth -= 1
        return [[self.clear_score, self.leveler, abs(self.timer), self.blocks, abs(self.blocks/self.timer), self.lines >= 40]]

    def rotate_stone_clockwise(self):
        if not self.gameover and not self.paused:
            new_stone = rotate_clockwise(self.stone)
            if not check_collision(self.board,
                                   new_stone,
                                   (self.stone_x, self.stone_y)):
                self.stone = new_stone

    def rotate_stone_counter_clockwise(self):
        if not self.gameover and not self.paused:
            new_stone = rotate_counter_clockwise(self.stone)
            if not check_collision(self.board,
                                   new_stone,
                                   (self.stone_x, self.stone_y)):
                self.stone = new_stone

    def rotate_reverse(self):
        if not self.gameover and not self.paused:
            new_stone = rotate_reverse(self.stone)
            if not check_collision(self.board,
                                   new_stone,
                                   (self.stone_x, self.stone_y)):
                self.stone = new_stone

    def switch_hold(self):
        if sum(self.hold_stone[0]) == 0 and not self.switched:
            self.hold_stone = tetris_shapes[max(self.stone[0])-1]
            self.new_stone()
        elif not self.switched:
            self.stone, self.hold_stone = self.hold_stone, tetris_shapes[max(self.stone[0])-1]
            self.stone_x = int(cols / 2 - len(self.stone[0])/2)

        self.switched = True

    def toggle_pause(self):
        self.paused = not self.paused

    def start_game(self):
        if self.gameover:
            self.init_game()
            self.gameover = False

    def run(self):
        key_actions = {
            'ESCAPE':   self.quit,
            'LEFT':     lambda:self.move(-1),
            'RIGHT':    lambda:self.move(+1),
            'DOWN':     lambda:self.drop(True),
            'UP':       self.rotate_stone_clockwise,
            'z':        self.rotate_stone_counter_clockwise,
            'a':        self.rotate_reverse,
            'p':        self.toggle_pause,
            'RETURN':    self.start_game,
            'SPACE':   self.insta_drop,
            'LSHIFT':    self.switch_hold
        }

        while 1:
            self.screen.fill((0,0,0))
            if self.gameover:
                self.center_msg("""Game Over!\nYour score: %.2f seconds with lines %d and blocks %d and PPS of %.2f
Press enter to continue""" % (abs(self.timer), self.lines, self.blocks, abs(self.blocks/self.timer)))
            else:
                if self.paused:
                    self.center_msg("Paused")
                else:
                    pygame.draw.line(self.screen,
                        (255,255,255),
                        (self.rlim+1, 0),
                        (self.rlim+1, self.height-1))
                    self.disp_msg("Next:", (
                        self.rlim+cell_size,
                        2))
                    self.disp_msg("Score: %d\n\nLevel: %d\
\nLines: %d" % (self.score, self.level, self.lines),
                        (self.rlim+cell_size, cell_size*5))
                    self.draw_matrix(self.bground_grid, (0,0))
                    self.draw_matrix(self.board, (0,0))
                    self.draw_matrix(self.stone,
                        (self.stone_x, self.stone_y))
                    self.draw_matrix(self.next_stone,
                        (cols+1,2))
                    self.draw_matrix(self.hold_stone, (cols+1, 15))
            pygame.display.update()

            for event in pygame.event.get():
                if event.type == pygame.USEREVENT+1:
                    #self.drop(False)
                    pass
                elif event.type == pygame.QUIT:
                    self.quit()
                elif event.type == pygame.KEYDOWN:
                    for key in key_actions:
                        if event.key == eval("pygame.K_"
                        +key):
                            key_actions[key]()

            self.dont_burn_my_cpu.tick(maxfps)

    def display(self):
        self.screen.fill((0, 0, 0))
        if self.gameover:
            self.center_msg("""Game Over!\nYour score: %d  with lines %d
        Press enter to continue""" % abs(self.timer), self.lines)
        else:
            if self.paused:
                self.center_msg("Paused")
            else:
                pygame.draw.line(self.screen,
                                 (255, 255, 255),
                                 (self.rlim + 1, 0),
                                 (self.rlim + 1, self.height - 1))
                self.disp_msg("Next:", (
                    self.rlim + cell_size,
                    2))
                self.disp_msg("Score: %d\n\nLevel: %d\
        \nLines: %d" % (self.score, self.level, self.lines),
                              (self.rlim + cell_size, cell_size * 5))
                self.draw_matrix(self.bground_grid, (0, 0))
                self.draw_matrix(self.board, (0, 0))
                self.draw_matrix(self.stone,
                                 (self.stone_x, self.stone_y))
                self.draw_matrix(self.next_stone,
                                 (cols + 1, 2))
                self.draw_matrix(self.hold_stone, (cols + 1, 15))
        pygame.display.update()

        self.dont_burn_my_cpu.tick(maxfps)

if __name__ == '__main__':
    for scorer in range(1, 11):
        for leveler in range(1, 11):
            for _ in range(50):
                data = pd.read_csv("Data.csv")
                App = TetrisApp(scorer, leveler)
                data_values = App.init_game()
                print(data_values)
                tempdf = pd.DataFrame(data_values, columns=["clear_score", "leveler", "time", "blocks", "pps", "win"])
                data = data.append(tempdf)
                data.to_csv("Data.csv", index=False)


