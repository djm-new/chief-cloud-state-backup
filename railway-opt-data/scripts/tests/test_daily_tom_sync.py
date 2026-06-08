import datetime as dt
import importlib.util
import pathlib
import sys
import unittest

SCRIPT_PATH = pathlib.Path('/opt/data/scripts/daily-tom-sync.py')
SPEC = importlib.util.spec_from_file_location('daily_tom_sync', SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class DailyTomSyncTests(unittest.TestCase):
    def test_build_section_strips_in_progress_marker_on_rollover(self) -> None:
        section = MODULE.build_section(
            dt.date(2026, 6, 8),
            [MODULE.Task(text='↗️ Prep deck [n:abc12]', group='Professional', id='abc12', priority=0, original_order=0)],
            [],
            {'tasks': {}},
        )

        self.assertNotIn('↗️', section)
        self.assertIn('Prep deck [n:abc12]', section)

    def test_parse_tasks_replaces_completed_x_with_checkmark(self) -> None:
        paras = [
            MODULE.Para(text='June 7, 2026', start=0, end=10),
            MODULE.Para(text='[Professional]', start=11, end=25),
            MODULE.Para(text='x Finish deck [n:abc12]', start=26, end=50),
        ]
        state = {'tasks': {}}

        carried, completed, replacements, in_progress, newly_parked = MODULE.parse_tasks(
            paras, 0, 3, dt.date(2026, 6, 8), state
        )

        self.assertEqual(carried, [])
        self.assertEqual(completed, ['abc12'])
        self.assertEqual(in_progress, [])
        self.assertEqual(newly_parked, [])
        self.assertEqual(len(replacements), 1)
        self.assertEqual(
            replacements[0]['replaceAllText']['containsText']['text'],
            'x Finish deck [n:abc12]',
        )
        self.assertEqual(
            replacements[0]['replaceAllText']['replaceText'],
            '✅ Finish deck [n:abc12]',
        )
        self.assertEqual(state['tasks']['abc12']['status'], 'completed')


if __name__ == '__main__':
    unittest.main()
