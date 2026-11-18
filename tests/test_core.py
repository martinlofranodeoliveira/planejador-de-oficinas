"""Exemplos públicos congelados antes da implementação do núcleo."""
import copy
import unittest

from planejador_oficinas import InputError, plan


def document():
    return {"slots": 2, "rooms": [{"id": "sala_a", "capacity": 10}],
            "workshops": [{"id": "arte", "duration": 1, "attendees": 5}]}


def scheduled(assignments, nodes, limit=20000):
    return {"status": "scheduled", "assignments": assignments,
            "stats": {"nodes": nodes, "limit": limit}}


class PublicCoreTests(unittest.TestCase):
    def test_empty_workshops_is_zero_node_solution(self):
        value = document()
        value["workshops"] = []
        self.assertEqual(plan(value), scheduled([], 0))

    def test_first_feasible_slot_and_closed_result(self):
        self.assertEqual(plan(document()), scheduled(
            [{"workshop": "arte", "room": "sala_a", "start": 0, "end": 1}], 1))

    def test_capacity_exclusion_proves_no_candidates(self):
        value = document()
        value["workshops"][0]["attendees"] = 11
        self.assertEqual(plan(value), {"status": "unsatisfiable", "assignments": [],
                                       "stats": {"nodes": 0, "limit": 20000}})

    def test_equipment_and_blocked_slots_filter_candidates(self):
        value = document()
        value["rooms"][0].update(resources=["projetor"], blocked=[0])
        value["workshops"][0]["resources"] = ["projetor"]
        self.assertEqual(plan(value), scheduled(
            [{"workshop": "arte", "room": "sala_a", "start": 1, "end": 2}], 1))
        value["rooms"][0]["resources"] = []
        self.assertEqual(plan(value)["status"], "unsatisfiable")

    def test_explicit_empty_permission_does_not_mean_all(self):
        for field in ("allowed_rooms", "allowed_starts"):
            with self.subTest(field=field):
                value = document()
                value["workshops"][0][field] = []
                self.assertEqual(plan(value)["stats"]["nodes"], 0)
                self.assertEqual(plan(value)["status"], "unsatisfiable")

    def test_allowed_room_and_start_are_observed(self):
        value = document()
        value["rooms"].append({"id": "sala_b", "capacity": 10})
        value["workshops"][0].update(allowed_rooms=["sala_b"], allowed_starts=[1])
        self.assertEqual(plan(value), scheduled(
            [{"workshop": "arte", "room": "sala_b", "start": 1, "end": 2}], 1))

    def test_conflict_attempt_count_and_adjacent_intervals(self):
        value = document()
        value["workshops"].append({"id": "leitura", "duration": 1, "attendees": 4})
        self.assertEqual(plan(value), scheduled([
            {"workshop": "arte", "room": "sala_a", "start": 0, "end": 1},
            {"workshop": "leitura", "room": "sala_a", "start": 1, "end": 2}], 3))

    def test_budget_exhaustion_is_not_infeasibility(self):
        value = document()
        value["workshops"].append({"id": "leitura", "duration": 1, "attendees": 4})
        self.assertEqual(plan(value, max_nodes=1), {
            "status": "budget_exhausted", "assignments": [], "stats": {"nodes": 1, "limit": 1}})
        self.assertEqual(plan(value, max_nodes=3)["status"], "scheduled")

    def test_instructor_and_group_conflicts_cross_rooms(self):
        for field in ("instructors", "groups"):
            with self.subTest(field=field):
                value = document()
                value["slots"] = 1
                value["rooms"].append({"id": "sala_b", "capacity": 10})
                value["workshops"][0][field] = ["pessoa_a"]
                value["workshops"].append({"id": "leitura", "duration": 1,
                                            "attendees": 4, field: ["pessoa_a"]})
                result = plan(value)
                self.assertEqual(result["status"], "unsatisfiable")
                self.assertEqual(result["assignments"], [])

    def test_distinct_roles_with_same_id_do_not_conflict(self):
        value = document()
        value["slots"] = 1
        value["rooms"].append({"id": "sala_b", "capacity": 10})
        value["workshops"][0]["instructors"] = ["pessoa_a"]
        value["workshops"].append({"id": "leitura", "duration": 1,
                                    "attendees": 4, "groups": ["pessoa_a"]})
        self.assertEqual(plan(value)["status"], "scheduled")

    def test_exact_types_unknown_fields_and_duplicates_rejected(self):
        invalid = [None, [], {"slots": 2}, dict(document(), unknown="SENTINEL_PRIVATE")]
        for field, bad in (("slots", True), ("rooms", ()), ("workshops", {})):
            value = document()
            value[field] = bad
            invalid.append(value)
        value = document()
        value["rooms"].append(copy.deepcopy(value["rooms"][0]))
        invalid.append(value)
        value = document()
        value["workshops"][0]["allowed_rooms"] = ["missing"]
        invalid.append(value)
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(InputError) as raised:
                plan(value)
            self.assertNotIn("SENTINEL_PRIVATE", str(raised.exception))
        for maximum in (True, 0, 200001, 1.0, "2"):
            with self.subTest(maximum=maximum), self.assertRaises(InputError):
                plan(document(), max_nodes=maximum)

    def test_preserves_inputs_permutation_and_result_freshness(self):
        value = document()
        value["rooms"].append({"id": "sala_b", "capacity": 10})
        value["workshops"].append({"id": "leitura", "duration": 1, "attendees": 4})
        before = copy.deepcopy(value)
        first = plan(value)
        self.assertEqual(value, before)
        permuted = copy.deepcopy(value)
        permuted["rooms"].reverse()
        permuted["workshops"].reverse()
        self.assertEqual(plan(permuted), first)
        first["assignments"].clear()
        self.assertNotEqual(plan(value)["assignments"], [])


if __name__ == "__main__":
    unittest.main()
