from tasks.project.packages.bot_state import BotState
from tasks.project.packages.adjacent_lanes import AdjacentLane
from tasks.project.packages.bot_name import BotName

LED_RED    = (1, 0, 0)
LED_GREEN  = (0, 1, 0)
LED_BLUE   = (0, 0, 1)
LED_YELLOW = (1, 1, 0)
LED_PURPLE = (1, 0, 1)
LED_CYAN   = (0, 1, 1)
LED_WHITE  = (1, 1, 1)

state_to_led_color = {
    BotState.convoying: LED_RED,
    BotState.waiting:   LED_GREEN,
    BotState.turning:   LED_BLUE,
    BotState.finishing: LED_WHITE
}

debugging = True

has_to_wait_predetermined = False # For testing. False if the bot doesn't need to yield
outgoing_lane_predetermined = AdjacentLane.west # For testing. None if the bot need to determine it

ROBOT_ID = BotName.megatron

start_in_manual_drive = True