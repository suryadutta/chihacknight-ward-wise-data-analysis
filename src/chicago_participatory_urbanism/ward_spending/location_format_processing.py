"""
Identify location description text format and parse into
street address or street intersection
"""

import re
from enum import Enum, auto
from typing import List

from src.chicago_participatory_urbanism.location_structures import (
    Intersection,
    Street,
    StreetAddress,
)


class LocationFormat(Enum):
    STREET_ADDRESS = auto()
    STREET_ADDRESS_RANGE = auto()
    INTERSECTION = auto()
    STREET_SEGMENT_INTERSECTIONS = auto()
    STREET_SEGMENT_ADDRESS_INTERSECTION = auto()
    STREET_SEGMENT_INTERSECTION_ADDRESS = auto()
    ALLEY = auto()
    UNIDENTIFIED = auto()


street_suffixes = (
    "(?:AVE|BLVD|CRES|CT|DR|ER|EXPY|HWY|LN|PKWY|PL|PLZ|RD|RL|ROW|SQ|SR|ST|TER|TOLL|WAY|XR|[A-Z])"
)
street_pattern = rf"[NWES]\s(.*)\s{street_suffixes}(?:|\s+[NWES])"
street_pattern_with_optional_suffix = rf"[NWES]\s(.*?)(?:\s{street_suffixes})?(?:|\s+[NWES])"
# special_street_names = "(?:S (AVENUE [A-Z])|N (BROADWAY)|N (LINCOLN PARK) W|W (MIDWAY PARK)|W (FULTON MARKET))"
# street_pattern = rf"(?:{street_pattern}|{special_street_names})"
# TO DO: get special street names working without breaking match.group(#) code

# TO DO: make regex robust against mistaking alley for intersection
location_patterns = {
    # Pattern for format: 1640 N MAPLEWOOD AVE
    LocationFormat.STREET_ADDRESS: rf"^\d+\s+{street_pattern}$",
    # Pattern for format: 434-442 E 46TH PL
    LocationFormat.STREET_ADDRESS_RANGE: rf"^(\d+)-(\d+)\s+({street_pattern})",
    # Pattern for format: N WOOD ST & W AUGUSTA BLVD & W CORTEZ ST & N HERMITAGE AVE
    # ALLEY NEEDS TO COME BEFORE INTERSECTION
    LocationFormat.ALLEY: rf"^{street_pattern_with_optional_suffix}\s*&\s*{street_pattern_with_optional_suffix}\s*&\s*{street_pattern_with_optional_suffix}\s*&\s*{street_pattern_with_optional_suffix}$",
    # Pattern for format: ON N LEAVITT ST FROM W DIVISION ST (1200 N) TO W NORTH AVE (1600 N)
    LocationFormat.STREET_SEGMENT_INTERSECTIONS: rf"^ON\s+{street_pattern}\s+FROM\s+{street_pattern}\s*\(\d+\s+[NWES]\)\s*TO\s+{street_pattern}\s*\(\d+\s+[NWES]\)$",
    # Pattern for format: ON W 52ND PL FROM 322 W TO S PRINCETON AVE (300 W)
    LocationFormat.STREET_SEGMENT_ADDRESS_INTERSECTION: rf"^ON\s+({street_pattern})\s+FROM\s+(\d+)\s+[NWES]\s+TO\s+{street_pattern}\s*\(\d+\s+[NWES]\)$",
    # Pattern for format: ON W 52ND PL FROM S PRINCETON AVE (300 W) TO 322 W
    LocationFormat.STREET_SEGMENT_INTERSECTION_ADDRESS: rf"^ON\s+({street_pattern})\s+FROM\s+{street_pattern}\s*\(\d+\s+[NWES]\)\s+TO\s+(\d+)\s+[NWES]$",
    # Pattern for format: N ASHLAND AVE & W CHESTNUT ST
    LocationFormat.INTERSECTION: rf"^{street_pattern}\s*&\s*{street_pattern}$",
}


def get_location_format(location):
    """Detect and return the address format."""
    for location_format, pattern in location_patterns.items():
        if re.match(pattern, location.strip()):
            return location_format

    return location_format.UNIDENTIFIED


def extract_street_address(street_address_text: str) -> StreetAddress:
    """Return StreetAddress for the STREET_ADDRESS format."""
    address_parts = street_address_text.strip().split(" ")
    number = int(address_parts[0])
    direction = address_parts[1]
    # capture multi-word names
    name = " ".join(address_parts[2:-1])
    street_type = address_parts[-1]

    street = Street(direction=direction, name=name, street_type=street_type)
    return StreetAddress(number=number, street=street)


def extract_segment_intersections(
    location_text: str,
) -> tuple[Intersection, Intersection]:
    """Return location data structures for the STREET_SEGMENT_INTERSECTIONS format."""
    # Format: ON N LEAVITT ST FROM W DIVISION ST (1200 N) TO W NORTH AVE (1600 N)
    pattern = location_patterns[LocationFormat.STREET_SEGMENT_INTERSECTIONS]
    # Check if the address matches the pattern
    match = re.match(pattern, location_text)
    if match:
        primary_street_name = match.group(1)
        cross_street1_name = match.group(2)
        cross_street2_name = match.group(3)

        primary_street = Street(direction="", name=primary_street_name, street_type="")
        cross_street1 = Street(direction="", name=cross_street1_name, street_type="")
        cross_street2 = Street(direction="", name=cross_street2_name, street_type="")

        intersection1 = Intersection(primary_street, cross_street1)
        intersection2 = Intersection(primary_street, cross_street2)

        return (intersection1, intersection2)
    else:
        return None, None


def extract_alley_intersections(location_text: str) -> List[Intersection]:
    """Return location data structures for the ALLEY location format"""
    match = re.match(location_patterns[LocationFormat.ALLEY], location_text)

    street_name1 = match.group(1)
    street_name2 = match.group(2)
    street_name3 = match.group(3)
    street_name4 = match.group(4)

    street1 = Street(direction="", name=street_name1, street_type="")
    street2 = Street(direction="", name=street_name2, street_type="")
    street3 = Street(direction="", name=street_name3, street_type="")
    street4 = Street(direction="", name=street_name4, street_type="")

    # get every possible intersection (streets aren't in any particular order)
    intersections = []
    intersections.append(Intersection(street1, street2))
    intersections.append(Intersection(street1, street3))
    intersections.append(Intersection(street1, street4))
    intersections.append(Intersection(street2, street3))
    intersections.append(Intersection(street2, street4))
    intersections.append(Intersection(street3, street4))

    return intersections


def extract_intersection(location_text: str) -> Intersection:
    """Return an Intersection for the INTERSECTION location format"""

    match = re.match(location_patterns[LocationFormat.INTERSECTION], location_text)
    street_name1 = match.group(1)
    street_name2 = match.group(2)

    street1 = Street(direction="", name=street_name1, street_type="")
    street2 = Street(direction="", name=street_name2, street_type="")
    intersection = Intersection(street1, street2)

    return intersection


def extract_address_range_street_addresses(
    location_text: str,
) -> tuple[StreetAddress, StreetAddress]:
    """Return location data structures for the STREET_ADDRESS_RANGE format"""
    match = re.match(location_patterns[LocationFormat.STREET_ADDRESS_RANGE], location_text)
    number1 = match.group(1)
    number2 = match.group(2)
    street = match.group(3)

    address1 = extract_street_address(f"{number1} {street}")
    address2 = extract_street_address(f"{number2} {street}")

    return (address1, address2)


def extract_segment_address_intersection_info(
    location_text: str,
) -> tuple[StreetAddress, Intersection]:
    """Return location data structures for the STREET_SEGMENT_ADDRESS_INTERSECTION format"""
    match = re.match(
        location_patterns[LocationFormat.STREET_SEGMENT_ADDRESS_INTERSECTION],
        location_text,
    )
    primary_street = match.group(1)
    primary_street_name = match.group(2)
    street_number = match.group(3)
    cross_street_name = match.group(4)

    street1 = Street(direction="", name=primary_street_name, street_type="")
    street2 = Street(direction="", name=cross_street_name, street_type="")
    intersection = Intersection(street1, street2)

    address = extract_street_address(f"{street_number} {primary_street}")

    return (address, intersection)


def extract_segment_intersection_address_info(
    location_text: str,
) -> tuple[Intersection, StreetAddress]:
    """Return location data structures for the STREET_SEGMENT_INTERSECTION_ADDRESS format"""
    match = re.match(
        location_patterns[LocationFormat.STREET_SEGMENT_INTERSECTION_ADDRESS],
        location_text,
    )
    primary_street = match.group(1)
    primary_street_name = match.group(2)
    cross_street_name = match.group(3)
    street_number = match.group(4)

    street1 = Street(direction="", name=primary_street_name, street_type="")
    street2 = Street(direction="", name=cross_street_name, street_type="")
    intersection = Intersection(street1, street2)

    address = extract_street_address(f"{street_number} {primary_street}")

    return (intersection, address)
