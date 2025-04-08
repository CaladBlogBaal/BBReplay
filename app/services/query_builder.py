from datetime import datetime
import typing

import sqlalchemy
from sqlalchemy import func, select, extract, and_, or_

from app.models.replay import Replay


class QueryBuilder:
    def __init__(self):
        pass

    @staticmethod
    def build_conditions(model, key, value, use_or=True):
        conditions = []

        if isinstance(value, str):
            value = value.strip().lower()
            conditions.append(func.lower(getattr(model, key)).like(f"%{value}%"))

        elif isinstance(value, datetime):
            day_condition = extract("day", getattr(model, key)) == value.day
            month_condition = extract("month", getattr(model, key)) == value.month
            hour_condition = extract("hour", getattr(model, key)) == value.hour
            minute_condition = extract("minute", getattr(model, key)) == value.minute
            conditions.extend([day_condition, month_condition, hour_condition, minute_condition])

        elif isinstance(value, tuple) or isinstance(value, list) and len(value) == 2:
            start, end = value
            conditions.append(getattr(model, key).between(start, end))

        else:
            conditions.append(getattr(model, key) == value)

        if use_or:
            return or_(*conditions)
        else:
            return and_(*conditions)

    def _build_group_flipped_equivalence_condition(self, model: typing.Type[Replay], normalized_params: dict[str, typing.Any], normalized_map: dict[str, str]):
        """
        Builds a condition that treats the entire group of p1/p2 parameters as interchangeable.
        Used to match scenarios like (p1 = A, p2 = B) OR (p1 = B, p2 = A), regardless of field pairing.
        Args:
            model: A pydantic BaseModel, used to represent a table.
            normalized_params: Normalized query parameters to ensure the pattern of p1_x is maintained.
            normalized_map: A map to undue any normalization of query parameters.
        Behavior:
            - Use stricter p1/p2 group-based matching when a valid pair is present
            - Otherwise, use flexible field flipping logic
        """

        p1_suffixes = {nk[2:] for nk in normalized_params if nk.startswith("p1")}
        p2_suffixes = {nk[2:] for nk in normalized_params if nk.startswith("p2")}

        has_valid_pair = bool(p1_suffixes & p2_suffixes)

        if has_valid_pair:
            # Use the old logic for strict pair matching
            p1_conditions = []
            p2_conditions = []
            flipped_p1_conditions = []
            flipped_p2_conditions = []

            for nk, val in normalized_params.items():
                # undue any normalization of query parameter keys to ensure it matches the model defined specification/class attributes
                orig_key = normalized_map[nk]

                if nk.startswith("p1"):
                    # Builds a condition like replays.p1 = value
                    p1_conditions.append(self.build_conditions(model, orig_key, val, use_or=False))
                    # Flipped condition: p1 -> p2
                    # Builds a condition like replays.p2 = value
                    flipped_key = "p2" + orig_key[2:]
                    flipped_p1_conditions.append(self.build_conditions(model, flipped_key, val, use_or=False))

                elif nk.startswith("p2"):
                    p2_conditions.append(self.build_conditions(model, orig_key, val, use_or=False))
                    flipped_key = "p1" + orig_key[2:]
                    flipped_p2_conditions.append(self.build_conditions(model, flipped_key, val, use_or=False))

            # ( p1_conditions and p2_conditions) or (flipped_p1_condition_p1 and flipped_p2_conditions)
            # To ensure pairings are equivalent regardless of side
            return or_(
                and_(*p1_conditions, *p2_conditions),
                and_(*flipped_p1_conditions, *flipped_p2_conditions)
            )

        else:
            # More flexible field logic to handle cases where no strict character pair is provided
            conditions = []
            flipped_conditions = []

            for nk, val in normalized_params.items():
                orig_key = normalized_map[nk]

                if nk.startswith("p1") or nk.startswith("p2"):
                    p1_key = "p1" + orig_key[2:]
                    flipped_key = "p2" + orig_key[2:]
                    # Builds a condition like replays.p1 = value
                    conditions.append(self.build_conditions(model, p1_key, val, use_or=False))
                    # Builds a condition like replays.p2 = value
                    flipped_conditions.append(self.build_conditions(model, flipped_key, val, use_or=False))

            # (conditions) or (flipped_conditions)
            # Ensures (p1 vs. p2) is interchangeable for satisfying the condition
            return or_(
                and_(*conditions),
                and_(*flipped_conditions)
        )

    def _build_pairwise_flippable_conditions(self, model: typing.Type[Replay], p1_fields: dict[str, typing.Any],
                                                 p2_fields: dict[str, typing.Any], normalized_map: dict[str, str],
                                                 strict_side: bool) -> typing.List:
        """
        Builds conditions that match each p1/p2 field pair and their flipped counterparts.
        Used for matching symmetric player values, not fields (e.g., p1_name = A AND p2_name = B OR p1_name = B AND p2_name = A.
        Honors strict_side if set.
        Args:
            model: A pydantic BaseModel, used to represent a table.
            p1_fields: Contains the p1_fields of the query parameters (e.g., p1, p1_toon).
            p2_fields: Contains the p2_fields of the query parameters (e.g., p2, p2_toon).
            normalized_map: A map to undue any normalization of query parameters.
        """
        conditions = []
        used_suffixes = set()

        for key1, val1 in p1_fields.items():
            suffix = key1[3:]
            key2 = f"p2_{suffix}"
            if key2 in p2_fields:
                val2 = p2_fields[key2]
                orig_key1 = normalized_map[key1]
                orig_key2 = normalized_map[key2]
                # Builds a condition like (replays.p1 = value AND replays.p2 = value2) OR (replays.p1 = value2 AND replays.p2 = value)
                conditions.append(or_(
                    and_(
                        self.build_conditions(model, orig_key1, val1, use_or=False),
                        self.build_conditions(model, orig_key2, val2, use_or=False)
                    ),
                    and_(
                        self.build_conditions(model, orig_key1, val2, use_or=False),
                        self.build_conditions(model, orig_key2, val1, use_or=False)
                    )
                ))
                used_suffixes.add(suffix)
            elif strict_side:
                # Not a flippable pair, just handle normally
                # Builds a condition like replays.p1 = value
                conditions.append(self.build_conditions(model, normalized_map[key1], val1, use_or=False))

        # Process p2 fields that do not have a corresponding p1 field to match
        for key2, val2 in p2_fields.items():
            suffix = key2[3:]
            if suffix not in used_suffixes and strict_side:
                conditions.append(self.build_conditions(model, normalized_map[key2], val2, use_or=False))

        return conditions

    def _build_other_conditions(self, model, other_params, normalized_map, use_or) -> typing.List:
        return [
            self.build_conditions(model, normalized_map[key], value, use_or)
            for key, value in other_params.items()
        ]

    def _normalize_params(self, params: dict) -> typing.Tuple[dict, dict]:
        normalized_params = {}
        normalized_map = {}

        for key, value in params.items():
            if key == "p1":
                nk = "p1_name"
            elif key == "p2":
                nk = "p2_name"
            else:
                nk = key

            normalized_map[nk] = key
            normalized_params[nk] = value

        return normalized_params, normalized_map

    def _group_params_by_prefix(self, params: dict) -> typing.Tuple[dict, dict, dict]:
        p1_fields = {}
        p2_fields = {}
        other_params = {}

        for nk, val in params.items():
            if nk.startswith("p1"):
                p1_fields[nk] = val
            elif nk.startswith("p2"):
                p2_fields[nk] = val
            else:
                other_params[nk] = val

        return p1_fields, p2_fields, other_params

    def build_query(self, model, query_params, use_or=True) -> sqlalchemy.sql.Select:
        """
        Args:
            model: A pydantic BaseModel, used to represent a table.
            query_params (dict): Filter parameters. Special key:
                - 'strict_side' (bool): If True, enforce exact p1/p2 matching; if False, allow symmetric behaviour ( default ).
            use_or (bool): Whether to use OR logic in multi-part field conditions.

        Returns:
            sqlalchemy.sql.Select: An SQL Select Query

        Behavior:
            - Groups fields by prefix into p1, p2, or other fields.
            - If strict_side is True:
                - Matches p1 fields to p1 and p2 fields to p2 (no symmetry or flipping of fields only values).
                - Unpaired fields matched as-is.
            - If strict_side is False:
                - Adds symmetric player side matching (e.g., P1 vs P2 == P2 vs P1), even to unpaired player fields.
                - Treats all p1/p2 fields as a group and flips them together(e.g. p1_fields/p2_fields == p1_flipped/p2_flipped)
                - Unpaired fields are matched as is.
        """
        params_copy = query_params.copy() # to not mutate the original dict
        strict_side = params_copy.pop("strict_side", False)

        query = select(model)
        normalized_params, normalized_map = self._normalize_params(params_copy)
        p1_fields, p2_fields, other_params = self._group_params_by_prefix(normalized_params)

        conditions = self._build_pairwise_flippable_conditions(
            model, p1_fields, p2_fields, normalized_map, strict_side
        )

        if not strict_side and any(k.startswith("p1") or k.startswith("p2") for k in normalized_params):
            flip_group_condition = self._build_group_flipped_equivalence_condition(model, normalized_params, normalized_map)
            conditions.append(flip_group_condition)

        other_conditions = self._build_other_conditions(model, other_params, normalized_map, use_or)
        conditions.extend(other_conditions)

        if conditions:
            query = query.where(and_(*conditions))

        return query