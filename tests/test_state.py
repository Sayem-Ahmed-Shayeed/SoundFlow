import unittest

from soundflow.core.state import DictationState, DictationStateMachine, InvalidTransition


class StateMachineTests(unittest.TestCase):
    def test_record_stop_drain_cycle(self):
        machine = DictationStateMachine()
        machine.start()
        self.assertEqual(machine.state, DictationState.RECORDING)
        machine.stop()
        self.assertEqual(machine.state, DictationState.DRAINING)
        machine.drained()
        self.assertEqual(machine.state, DictationState.IDLE)

    def test_push_to_talk_cannot_restart_while_draining(self):
        machine = DictationStateMachine()
        machine.start()
        machine.stop()
        with self.assertRaises(InvalidTransition):
            machine.start()

    def test_error_is_recoverable(self):
        machine = DictationStateMachine()
        machine.fail("microphone unavailable")
        machine.start()
        self.assertEqual(machine.state, DictationState.RECORDING)


if __name__ == "__main__":
    unittest.main()

