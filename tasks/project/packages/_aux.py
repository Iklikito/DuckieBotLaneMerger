import time

from tasks.project.packages.settings import state_to_led_color, debugging, color_coded_leds
from tasks.project.packages.bot_state import BotState
from tasks.project.packages.bot_name import BotName

state_to_state_entrance_console_message = {
    BotState.convoying : "Bot started. Convoying...",
    BotState.waiting   : "Waiting for lanes on the right to clear...",
    BotState.turning   : "Lanes on the right are clear. Turning...",
    BotState.finishing : "Entered the outgoing lane. Finishing..."
}

state_to_next_state = {
    None               : BotState.convoying,
    BotState.convoying : BotState.waiting,
    BotState.waiting   : BotState.turning,
    BotState.turning   : BotState.finishing,
    BotState.finishing : BotState.finishing
}

def set_all_leds(leds, color):
    if leds:
        leds.set_rgb(0, color)
        leds.set_rgb(2, color)
        leds.set_rgb(3, color)
        leds.set_rgb(4, color)

def set_front_leds(leds, color):
    if leds:
        leds.set_rgb(0, color)
        leds.set_rgb(2, color)

def set_back_leds(leds, color):
    if leds:
        leds.set_rgb(3, color)
        leds.set_rgb(4, color)

def set_right_leds(leds, color):
    if leds:
        leds.set_rgb(2, color)
        leds.set_rgb(4, color)

def set_left_leds(leds, color):
    if leds:
        leds.set_rgb(0, color)
        leds.set_rgb(3, color)

def get_next_state(state: BotState) -> BotState:
    try:
        return state_to_next_state[state]
    except KeyError:
        error_message = f"The function get_next_state cannot handle {state}"
        raise ValueError(error_message)

def get_state_entrance_console_message(state: BotState) -> str:
    return state_to_state_entrance_console_message[state]

def get_next_state_and_set_leds_if_possible(state: BotState, leds) -> BotState:
    next_state = get_next_state(state)
    next_led_color = state_to_led_color[next_state]
    if color_coded_leds:
        set_front_leds(leds, next_led_color)

    if debugging:
        console_message = get_state_entrance_console_message(next_state)
        print(console_message)
    
    return next_state
    
def debug_print(message, debugging=False):
    if not debugging:
        return
    
    timestamp = time.strftime('%H:%M:%S', time.localtime()) + f'.{int(time.time() * 1000) % 1000:03d}'
    print(f'[{timestamp}] {message}')