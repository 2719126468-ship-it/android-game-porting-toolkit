/*
 * AGPT Orbit Snake - an original portable SDL2 mini-game.
 * Copyright (c) 2026 AGPT contributors.
 * SPDX-License-Identifier: MIT
 */
#include <SDL.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <time.h>

#define SCREEN_W 480
#define SCREEN_H 800
#define GRID_W 22
#define GRID_H 28
#define CELL 18
#define BOARD_X ((SCREEN_W - GRID_W * CELL) / 2)
#define BOARD_Y 145
#define MAX_CELLS (GRID_W * GRID_H)
#define MOVE_INTERVAL 135u

typedef enum { DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT } Direction;

static int snake_x[MAX_CELLS];
static int snake_y[MAX_CELLS];
static int snake_length;
static int food_x;
static int food_y;
static int score;
static Direction direction;
static bool started;
static bool game_over;
static Uint32 last_step;

static void set_color(SDL_Renderer *renderer, Uint8 r, Uint8 g, Uint8 b, Uint8 a)
{
    SDL_SetRenderDrawColor(renderer, r, g, b, a);
}

static void fill_rect(SDL_Renderer *renderer, int x, int y, int w, int h)
{
    SDL_Rect rect = { x, y, w, h };
    SDL_RenderFillRect(renderer, &rect);
}

static bool opposite(Direction a, Direction b)
{
    return ((int)a + 2) % 4 == (int)b;
}

static bool occupies(int x, int y, int count)
{
    for (int i = 0; i < count; ++i) {
        if (snake_x[i] == x && snake_y[i] == y) {
            return true;
        }
    }
    return false;
}

static void spawn_food(void)
{
    for (int attempts = 0; attempts < MAX_CELLS * 2; ++attempts) {
        int x = rand() % GRID_W;
        int y = rand() % GRID_H;
        if (!occupies(x, y, snake_length)) {
            food_x = x;
            food_y = y;
            return;
        }
    }
    game_over = true;
}

static void reset_game(void)
{
    snake_length = 5;
    int start_x = GRID_W / 2;
    int start_y = GRID_H / 2;
    for (int i = 0; i < snake_length; ++i) {
        snake_x[i] = start_x - i;
        snake_y[i] = start_y;
    }
    direction = DIR_RIGHT;
    score = 0;
    started = true;
    game_over = false;
    last_step = SDL_GetTicks();
    spawn_food();
}

static void change_direction(Direction next)
{
    if (!opposite(direction, next)) {
        direction = next;
        started = true;
    }
}

static void apply_touch(int x, int y)
{
    if (game_over) {
        reset_game();
        return;
    }
    /* The lower control pad remains usable without swipe gestures. */
    if (y >= 680) {
        if (y < 735) {
            change_direction(DIR_UP);
        } else if (y > 770) {
            change_direction(DIR_DOWN);
        } else if (x < 215) {
            change_direction(DIR_LEFT);
        } else if (x > 265) {
            change_direction(DIR_RIGHT);
        }
    }
}

static void apply_swipe(int x0, int y0, int x1, int y1)
{
    int dx = x1 - x0;
    int dy = y1 - y0;
    if (abs(dx) < 18 && abs(dy) < 18) {
        apply_touch(x1, y1);
        return;
    }
    if (abs(dx) > abs(dy)) {
        change_direction(dx > 0 ? DIR_RIGHT : DIR_LEFT);
    } else {
        change_direction(dy > 0 ? DIR_DOWN : DIR_UP);
    }
}

static bool step_game(void)
{
    int next_x = snake_x[0];
    int next_y = snake_y[0];
    switch (direction) {
        case DIR_UP:    --next_y; break;
        case DIR_RIGHT: ++next_x; break;
        case DIR_DOWN:  ++next_y; break;
        case DIR_LEFT:  --next_x; break;
    }
    if (next_x < 0 || next_x >= GRID_W || next_y < 0 || next_y >= GRID_H) {
        game_over = true;
        return false;
    }

    bool eating = (next_x == food_x && next_y == food_y);
    int collision_count = eating ? snake_length : snake_length - 1;
    if (occupies(next_x, next_y, collision_count)) {
        game_over = true;
        return false;
    }

    if (eating && snake_length < MAX_CELLS) {
        ++snake_length;
        score += 10;
    }
    for (int i = snake_length - 1; i > 0; --i) {
        snake_x[i] = snake_x[i - 1];
        snake_y[i] = snake_y[i - 1];
    }
    snake_x[0] = next_x;
    snake_y[0] = next_y;
    if (eating) {
        spawn_food();
    }
    return true;
}

static void draw_digit(SDL_Renderer *renderer, int x, int y, int digit)
{
    static const Uint8 masks[10] = {
        0x3f, 0x06, 0x5b, 0x4f, 0x66,
        0x6d, 0x7d, 0x07, 0x7f, 0x6f
    };
    const int w = 19;
    const int h = 35;
    const int t = 4;
    const int mid = h / 2;
    Uint8 mask = masks[digit % 10];
    set_color(renderer, 150, 255, 190, 255);
    if (mask & 0x01) fill_rect(renderer, x + t, y, w - 2 * t, t);
    if (mask & 0x02) fill_rect(renderer, x + w - t, y + t, t, mid - t);
    if (mask & 0x04) fill_rect(renderer, x + w - t, y + mid, t, mid - t);
    if (mask & 0x08) fill_rect(renderer, x + t, y + h - t, w - 2 * t, t);
    if (mask & 0x10) fill_rect(renderer, x, y + mid, t, mid - t);
    if (mask & 0x20) fill_rect(renderer, x, y + t, t, mid - t);
    if (mask & 0x40) fill_rect(renderer, x + t, y + mid - t / 2, w - 2 * t, t);
}

static void draw_arrow(SDL_Renderer *renderer, int cx, int cy, Direction dir)
{
    set_color(renderer, 190, 235, 205, 255);
    if (dir == DIR_UP || dir == DIR_DOWN) {
        int sign = dir == DIR_UP ? -1 : 1;
        for (int i = 0; i < 13; ++i) {
            fill_rect(renderer, cx - i, cy + sign * i, 2 * i + 1, 3);
        }
        fill_rect(renderer, cx - 5, cy - sign * 1, 10, 15);
    } else {
        int sign = dir == DIR_LEFT ? -1 : 1;
        for (int i = 0; i < 13; ++i) {
            fill_rect(renderer, cx + sign * i, cy - i, 3, 2 * i + 1);
        }
        fill_rect(renderer, cx - sign * 15, cy - 5, 15, 10);
    }
}

static void draw_button(SDL_Renderer *renderer, int x, int y, Direction dir)
{
    SDL_Rect button = { x - 22, y - 22, 44, 44 };
    set_color(renderer, 31, 55, 47, 255);
    SDL_RenderFillRect(renderer, &button);
    set_color(renderer, 76, 130, 101, 255);
    SDL_RenderDrawRect(renderer, &button);
    draw_arrow(renderer, x, y, dir);
}

static void render_game(SDL_Renderer *renderer)
{
    set_color(renderer, 9, 17, 16, 255);
    SDL_RenderClear(renderer);

    /* Top status panel and score. */
    set_color(renderer, 24, 44, 38, 255);
    fill_rect(renderer, 26, 26, 428, 82);
    set_color(renderer, 64, 111, 86, 255);
    fill_rect(renderer, 26, 26, 5, 82);
    int value = score;
    int digits[6];
    int count = 0;
    do {
        digits[count++] = value % 10;
        value /= 10;
    } while (value > 0 && count < 6);
    for (int i = 0; i < count; ++i) {
        draw_digit(renderer, 48 + i * 26, 49, digits[count - i - 1]);
    }

    /* Board and subtle grid. */
    set_color(renderer, 16, 30, 26, 255);
    fill_rect(renderer, BOARD_X - 5, BOARD_Y - 5, GRID_W * CELL + 10, GRID_H * CELL + 10);
    set_color(renderer, 35, 54, 47, 255);
    for (int x = 0; x <= GRID_W; ++x) {
        int px = BOARD_X + x * CELL;
        SDL_RenderDrawLine(renderer, px, BOARD_Y, px, BOARD_Y + GRID_H * CELL);
    }
    for (int y = 0; y <= GRID_H; ++y) {
        int py = BOARD_Y + y * CELL;
        SDL_RenderDrawLine(renderer, BOARD_X, py, BOARD_X + GRID_W * CELL, py);
    }

    /* Food. */
    int fx = BOARD_X + food_x * CELL;
    int fy = BOARD_Y + food_y * CELL;
    set_color(renderer, 255, 169, 92, 255);
    fill_rect(renderer, fx + 4, fy + 2, CELL - 8, CELL - 4);
    fill_rect(renderer, fx + 2, fy + 4, CELL - 4, CELL - 8);
    set_color(renderer, 255, 224, 164, 255);
    fill_rect(renderer, fx + 7, fy + 5, 4, 4);

    /* Snake. */
    for (int i = snake_length - 1; i >= 0; --i) {
        int sx = BOARD_X + snake_x[i] * CELL;
        int sy = BOARD_Y + snake_y[i] * CELL;
        if (i == 0) {
            set_color(renderer, 175, 255, 198, 255);
        } else {
            set_color(renderer, 62, 190, 122, 255);
        }
        fill_rect(renderer, sx + 2, sy + 2, CELL - 4, CELL - 4);
        if (i == 0) {
            set_color(renderer, 12, 40, 29, 255);
            fill_rect(renderer, sx + 5, sy + 5, 3, 3);
            fill_rect(renderer, sx + 11, sy + 5, 3, 3);
        }
    }

    /* Touch control pad. */
    draw_button(renderer, 240, 711, DIR_UP);
    draw_button(renderer, 187, 759, DIR_LEFT);
    draw_button(renderer, 293, 759, DIR_RIGHT);
    draw_button(renderer, 240, 785, DIR_DOWN);

    if (game_over) {
        SDL_Rect panel = { 100, 360, 280, 88 };
        set_color(renderer, 93, 37, 39, 235);
        SDL_SetRenderDrawBlendMode(renderer, SDL_BLENDMODE_BLEND);
        SDL_RenderFillRect(renderer, &panel);
        set_color(renderer, 255, 178, 150, 255);
        SDL_RenderDrawRect(renderer, &panel);
        fill_rect(renderer, 222, 386, 36, 36);
        set_color(renderer, 93, 37, 39, 255);
        SDL_Point p1 = { 232, 393 };
        SDL_Point p2 = { 232, 415 };
        SDL_Point p3 = { 250, 404 };
        SDL_RenderDrawLine(renderer, p1.x, p1.y, p2.x, p2.y);
        SDL_RenderDrawLine(renderer, p2.x, p2.y, p3.x, p3.y);
        SDL_RenderDrawLine(renderer, p3.x, p3.y, p1.x, p1.y);
        SDL_SetRenderDrawBlendMode(renderer, SDL_BLENDMODE_NONE);
    }

    SDL_RenderPresent(renderer);
}

int main(int argc, char *argv[])
{
    (void)argc;
    (void)argv;
    srand((unsigned int)time(NULL));

    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_TIMER | SDL_INIT_EVENTS) != 0) {
        SDL_Log("SDL_Init failed: %s", SDL_GetError());
        return 1;
    }

    SDL_SetHint(SDL_HINT_RENDER_SCALE_QUALITY, "0");
    SDL_Window *window = SDL_CreateWindow(
        "AGPT Orbit Snake",
        SDL_WINDOWPOS_UNDEFINED,
        SDL_WINDOWPOS_UNDEFINED,
        SCREEN_W,
        SCREEN_H,
        SDL_WINDOW_SHOWN | SDL_WINDOW_ALLOW_HIGHDPI
    );
    if (window == NULL) {
        SDL_Log("SDL_CreateWindow failed: %s", SDL_GetError());
        SDL_Quit();
        return 1;
    }

    SDL_Renderer *renderer = SDL_CreateRenderer(
        window, -1, SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC
    );
    if (renderer == NULL) {
        renderer = SDL_CreateRenderer(window, -1, SDL_RENDERER_SOFTWARE);
    }
    if (renderer == NULL) {
        SDL_Log("SDL_CreateRenderer failed: %s", SDL_GetError());
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    SDL_RenderSetLogicalSize(renderer, SCREEN_W, SCREEN_H);
    SDL_RenderSetIntegerScale(renderer, SDL_FALSE);

    reset_game();
    bool running = true;
    int touch_x = 0;
    int touch_y = 0;
    bool mouse_down = false;
    int mouse_x = 0;
    int mouse_y = 0;

    while (running) {
        SDL_Event event;
        while (SDL_PollEvent(&event)) {
            switch (event.type) {
                case SDL_QUIT:
                    running = false;
                    break;
                case SDL_KEYDOWN:
                    if (event.key.keysym.sym == SDLK_ESCAPE) {
                        running = false;
                    } else if (event.key.keysym.sym == SDLK_UP || event.key.keysym.sym == SDLK_w) {
                        change_direction(DIR_UP);
                    } else if (event.key.keysym.sym == SDLK_RIGHT || event.key.keysym.sym == SDLK_d) {
                        change_direction(DIR_RIGHT);
                    } else if (event.key.keysym.sym == SDLK_DOWN || event.key.keysym.sym == SDLK_s) {
                        change_direction(DIR_DOWN);
                    } else if (event.key.keysym.sym == SDLK_LEFT || event.key.keysym.sym == SDLK_a) {
                        change_direction(DIR_LEFT);
                    } else if (event.key.keysym.sym == SDLK_SPACE && game_over) {
                        reset_game();
                    }
                    break;
                case SDL_FINGERDOWN:
                    touch_x = (int)(event.tfinger.x * SCREEN_W);
                    touch_y = (int)(event.tfinger.y * SCREEN_H);
                    break;
                case SDL_FINGERUP: {
                    int x = (int)(event.tfinger.x * SCREEN_W);
                    int y = (int)(event.tfinger.y * SCREEN_H);
                    apply_swipe(touch_x, touch_y, x, y);
                    break;
                }
                case SDL_MOUSEBUTTONDOWN:
                    mouse_down = true;
                    mouse_x = event.button.x;
                    mouse_y = event.button.y;
                    break;
                case SDL_MOUSEBUTTONUP:
                    if (mouse_down) {
                        apply_swipe(mouse_x, mouse_y, event.button.x, event.button.y);
                    }
                    mouse_down = false;
                    break;
                default:
                    break;
            }
        }

        Uint32 now = SDL_GetTicks();
        if (!game_over && started && now - last_step >= MOVE_INTERVAL) {
            (void)step_game();
            last_step = now;
        }
        render_game(renderer);
        SDL_Delay(8);
    }

    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return 0;
}
