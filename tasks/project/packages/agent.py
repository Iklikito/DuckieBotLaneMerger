from tasks.project.packages.MergeAgent import MergeAgent

def main(camera, wheels, leds, stop_event, debug=None, debug_lock=None, cmd_queue=None):
    merge_agent = MergeAgent(camera, wheels, leds, stop_event, debug, debug_lock, cmd_queue)
    merge_agent.run()