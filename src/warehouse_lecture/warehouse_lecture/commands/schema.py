"""RobotCommand schema (pydantic) shared by the parser, the executor and the dialog manager.

The pydantic model is what Structured Outputs enforces; ``validate()`` then checks the
*meaning* against the world (known places, objects, poses) and fills defaults, which a
JSON schema cannot do. ``to_msg``/``from_msg`` convert to warehouse_interfaces/RobotCommand.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field
from warehouse_interfaces.msg import KeyValue, RobotCommand as RobotCommandMsg

PARCELS = ("parcel_red", "parcel_blue", "parcel_yellow")
FIND_TARGETS = ("person", "forklift", "pallet", "cone", "extinguisher") + PARCELS
ARM_POSES = ("ready", "hands_up", "transport", "home")
GRIPPER = ("open", "close")
STATIONS = ("pick_table", "place_table")
PLACE_KO = {"pick_table": "픽업 작업대", "place_table": "적재 작업대", "rack_a": "랙 A", "rack_b": "랙 B", "rack_c": "랙 C", "rack_d": "랙 D",
            "rack_e": "랙 E", "rack_f": "랙 F", "center_aisle": "중앙 통로", "east_wall": "동쪽 벽", "west_wall": "서쪽 벽"}
TARGET_KO = {"parcel_red": "빨간 상자", "parcel_blue": "파란 상자", "parcel_yellow": "노란 상자", "person": "사람", "forklift": "지게차",
             "pallet": "팔레트", "cone": "콘", "extinguisher": "소화기"}


class Intent(str, Enum):
    move_object = "move_object"
    go_to = "go_to"
    find = "find"
    report = "report"
    answer = "answer"
    arm_pose = "arm_pose"
    gripper = "gripper"
    stop = "stop"


class Place(str, Enum):
    none = ""
    pick_table = "pick_table"
    place_table = "place_table"
    rack_a = "rack_a"
    rack_b = "rack_b"
    rack_c = "rack_c"
    rack_d = "rack_d"
    rack_e = "rack_e"
    rack_f = "rack_f"
    center_aisle = "center_aisle"
    east_wall = "east_wall"
    west_wall = "west_wall"


class Attributes(BaseModel):
    helmet: Optional[str] = Field(None, description='"true" 또는 "false"')
    vest: Optional[str] = Field(None, description="orange | green | none")


class RobotCommand(BaseModel):
    """One structured command. Field names match warehouse_interfaces/RobotCommand."""

    intent: Intent
    target: str = Field("", description="물체(parcel_red 등)·person·자세(ready, hands_up, transport, home)·그리퍼(open, close)")
    source: Place = Place.none
    destination: Place = Place.none
    attributes: Attributes = Field(default_factory=Attributes)
    reply: str = Field("", description="사용자에게 할 한 문장 (되묻기·거부 포함)")

    # --- semantic validation ------------------------------------------------
    def validate_world(self):
        """Fill defaults and return a list of problems (empty = executable)."""
        problems = []
        i = self.intent
        if i == Intent.move_object:
            if self.target not in PARCELS:
                problems.append(f"옮길 상자가 정해지지 않았다: {self.target!r} (parcel_red/blue/yellow)")
            if self.source == Place.none:
                self.source = Place.pick_table
            if self.destination == Place.none:
                self.destination = Place.place_table
            if self.source.value not in STATIONS or self.destination.value not in STATIONS:
                problems.append("상자는 작업대(pick_table, place_table) 사이에서만 옮길 수 있다")
            if self.source == self.destination:
                problems.append("출발 작업대와 도착 작업대가 같다")
        elif i == Intent.go_to:
            if self.destination == Place.none:
                problems.append("목적지가 없다")
        elif i == Intent.find:
            if self.target not in FIND_TARGETS:
                problems.append(f"찾을 대상이 정해지지 않았다: {self.target!r}")
        elif i == Intent.arm_pose:
            if self.target not in ARM_POSES:
                problems.append(f"모르는 팔 자세 {self.target!r} ({', '.join(ARM_POSES)})")
        elif i == Intent.gripper:
            if self.target not in GRIPPER:
                problems.append(f"그리퍼는 open/close 만 된다: {self.target!r}")
        return problems

    def attribute_dict(self):
        return {k: v for k, v in self.attributes.model_dump().items() if v}

    # --- ROS conversion -----------------------------------------------------
    def to_msg(self, utterance="", request_id=""):
        msg = RobotCommandMsg()
        msg.request_id, msg.intent, msg.target = request_id, self.intent.value, self.target
        msg.source, msg.destination, msg.utterance = self.source.value, self.destination.value, utterance
        msg.params = [KeyValue(key=k, value=str(v)) for k, v in self.attribute_dict().items()]
        if self.reply:
            msg.params.append(KeyValue(key="reply", value=self.reply))
        return msg

    @classmethod
    def from_msg(cls, msg):
        params = {kv.key: kv.value for kv in msg.params}
        return cls(intent=Intent(msg.intent), target=msg.target, source=Place(msg.source or ""), destination=Place(msg.destination or ""),
                   attributes=Attributes(helmet=params.get("helmet"), vest=params.get("vest")), reply=params.get("reply", ""))

    def describe(self):
        """Short Korean description for logs and confirmations."""
        names = {"parcel_red": "빨간 상자", "parcel_blue": "파란 상자", "parcel_yellow": "노란 상자", "person": "사람"}
        t = names.get(self.target, self.target)
        if self.intent == Intent.move_object:
            return f"{t}를 {self.source.value}에서 {self.destination.value}로 옮기기"
        if self.intent == Intent.go_to:
            return f"{self.destination.value}로 이동"
        if self.intent == Intent.find:
            return f"{t} 찾기 {self.attribute_dict() or ''}".strip()
        return f"{self.intent.value} {self.target}".strip()
