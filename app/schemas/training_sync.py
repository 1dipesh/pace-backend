from datetime import date
from pydantic import AwareDatetime as datetime
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.schemas.nutrition_sync import Id, Text

Number = Annotated[float, Field(ge=0, le=999999, allow_inf_nan=False)]
Count = Annotated[int, Field(ge=0, le=32767)]
Seconds = Annotated[int, Field(ge=0, le=31536000)]
Notes = Annotated[str, Field(max_length=10000)]
Mode = Literal['weight_reps', 'bodyweight_reps', 'duration']
Muscle = Literal['chest','back','shoulders','biceps','triceps','quads','hamstrings','glutes','calves','core','full-body','other']
Equipment = Literal['barbell','dumbbell','machine','cable','bodyweight','kettlebell','smith-machine','other']
Entity = Literal['exercises','templates','workouts','settings','activities','hybrid']

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Record(Strict):
    id: Id
    createdAt: datetime
    updatedAt: datetime

class Exercise(Record):
    name: Text
    primaryMuscle: Muscle
    secondaryMuscles: list[Muscle] = Field(max_length=20)
    equipment: Equipment
    trackingMode: Mode
    isStarter: bool
    isFavorite: bool | None = None
    notes: Notes | None = None
    archivedAt: datetime | None = None

class TemplateItem(Strict):
    exerciseId: Id
    order: Count
    targetSets: int = Field(ge=1, le=100)
    warmupSets: int | None = Field(default=None, ge=0, le=100)
    restSeconds: Seconds | None = Field(default=None, le=3600)
    note: Notes | None = None

class Template(Record):
    name: Text
    items: list[TemplateItem] = Field(min_length=1, max_length=100)
    notes: Notes | None = None
    sourceProgramId: str | None = Field(default=None, max_length=120)
    sourceProgramVariantId: str | None = Field(default=None, max_length=120)
    sourceProgramDayId: str | None = Field(default=None, max_length=120)
    sourceProgramName: Text | None = None
    usageCount: int | None = Field(default=None, ge=0)
    lastUsedAt: datetime | None = None

class Session(Record):
    status: Literal['completed']
    date: date
    templateId: Id | None = None
    name: Text
    startedAt: datetime
    endedAt: datetime
    notes: Notes | None = None

    @model_validator(mode='after')
    def times(self):
        if self.endedAt < self.startedAt: raise ValueError('Workout ends before it starts')
        return self

class Log(Record):
    sessionId: Id
    exerciseId: Id
    exerciseName: Text
    order: Count
    trackingMode: Mode | None = None
    primaryMuscle: Muscle | None = None
    equipment: Equipment | None = None
    restSeconds: Seconds | None = Field(default=None, le=3600)
    notes: Notes | None = None

class Set(Record):
    sessionId: Id
    exerciseLogId: Id
    exerciseId: Id
    setNumber: int = Field(ge=1, le=32767)
    setType: Literal['warmup','working']
    weight: Number | None = None
    weightUnit: Literal['kg','lb'] | None = None
    reps: Count | None = Field(default=None, le=1000)
    durationSeconds: Seconds | None = Field(default=None, le=86400)
    effortMode: Literal['rir','rpe'] | None = None
    effortValue: float | None = Field(default=None, ge=0, le=10, allow_inf_nan=False)
    restSeconds: Seconds | None = Field(default=None, le=3600)
    completedAt: datetime | None = None

    @model_validator(mode='after')
    def effort(self):
        if self.effortValue is not None and (self.effortMode is None or (self.effortMode == 'rpe' and self.effortValue < 1)):
            raise ValueError('Invalid effort value/mode')
        return self

class Bundle(Strict):
    log: Log
    sets: list[Set] = Field(max_length=200)

class Workout(Strict):
    id: Id
    session: Session
    exercises: list[Bundle] = Field(max_length=100)

    @model_validator(mode='after')
    def links(self):
        if self.id != self.session.id: raise ValueError('Workout/session id mismatch')
        ids = set()
        for bundle in self.exercises:
            log = bundle.log
            if log.sessionId != self.id or log.id in ids: raise ValueError('Invalid workout log ownership')
            ids.add(log.id)
            for s in bundle.sets:
                if s.sessionId != self.id or s.exerciseLogId != log.id or s.exerciseId != log.exerciseId or s.id in ids:
                    raise ValueError('Invalid set ownership')
                ids.add(s.id)
        return self

class Settings(Record):
    id: Literal['default']
    effortMode: Literal['rir','rpe','off']
    autoStartRestTimer: bool
    workingRestSeconds: int = Field(ge=0, le=3600)
    warmupRestSeconds: int = Field(ge=0, le=3600)
    plateCalculatorUnit: Literal['kg','lb']
    plateCalculatorKgBarWeight: Number
    plateCalculatorLbBarWeight: Number
    plateCalculatorKgPlates: list[Annotated[float, Field(gt=0, le=1000, allow_inf_nan=False)]] = Field(min_length=1, max_length=100)
    plateCalculatorLbPlates: list[Annotated[float, Field(gt=0, le=1000, allow_inf_nan=False)]] = Field(min_length=1, max_length=100)

class Activity(Record):
    type: Literal['running','walking','cycling','football','basketball','rowing','swimming','other']
    name: Text
    date: date
    durationSeconds: int = Field(ge=1, le=172800)
    distanceKm: Number | None = Field(default=None, le=10000)
    notes: Notes | None = None

class Segment(Strict):
    id: Id
    order: Count
    kind: Literal['run','station']
    label: Text
    stationType: Literal['ski_erg','sled_push','sled_pull','burpee_broad_jump','rowing','farmers_carry','sandbag_lunges','wall_balls','other'] | None = None
    targetDistanceMeters: Number | None = Field(default=None, le=100000)
    targetReps: Count | None = Field(default=None, le=10000)
    loadKg: Number | None = Field(default=None, le=5000)
    startedAt: datetime | None = None
    completedAt: datetime | None = None
    durationSeconds: Seconds | None = Field(default=None, le=172800)

    @model_validator(mode='after')
    def segment_times(self):
        if self.startedAt and self.completedAt and self.completedAt < self.startedAt: raise ValueError('Split ends before it starts')
        return self

class Hybrid(Session):
    preset: Literal['hyrox_full','hyrox_half','hyrox_stations','custom']
    segments: list[Segment] = Field(min_length=1, max_length=200)

    @model_validator(mode='after')
    def unique_segments(self):
        if len({s.id for s in self.segments}) != len(self.segments): raise ValueError('Duplicate segment id')
        return self

SCHEMAS = dict(exercises=Exercise, templates=Template, workouts=Workout, settings=Settings, activities=Activity, hybrid=Hybrid)

class Change(Strict):
    entity: Entity
    id: Id
    expected_version: int = Field(ge=0)
    data: dict | None

    @model_validator(mode='after')
    def validate_data(self):
        if self.entity == 'settings' and self.id != 'default': raise ValueError('Settings id must be default')
        if self.data is not None and SCHEMAS[self.entity].model_validate(self.data).id != self.id:
            raise ValueError('Record id mismatch')
        return self

class Mutation(Strict):
    mutation_id: UUID
    changes: list[Change] = Field(min_length=1, max_length=100)

    @model_validator(mode='after')
    def keys_and_size(self):
        if len({(c.entity,c.id) for c in self.changes}) != len(self.changes): raise ValueError('Duplicate record key')
        if len(self.model_dump_json()) > 4000000: raise ValueError('Training batch exceeds 4 MB')
        return self
