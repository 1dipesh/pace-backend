"""Lossless Alcohol documents; active sessions are local to their recorder."""
import json
from datetime import date
from typing import Annotated, Literal
from uuid import UUID
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator
from app.schemas.nutrition_sync import Id

Finite = Annotated[float, Field(ge=0, le=10000000, allow_inf_nan=False)]
Volume = Annotated[float, Field(gt=0, le=10000, allow_inf_nan=False)]
Category = Literal['beer','wine','spirit','cocktail','other']

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Record(Strict):
    id: Id
    createdAt: AwareDatetime

class Updated(Record):
    updatedAt: AwareDatetime

class Session(Updated):
    startedAt: AwareDatetime
    endedAt: AwareDatetime
    status: Literal['ended']
    entryMode: Literal['live','backdated'] = 'live'
    historicalDate: date | None = None
    notes: str | None = Field(default=None, max_length=10000)
    pausedAt: None = None
    totalPausedMs: int = Field(default=0, ge=0, le=2147483647000)

    @model_validator(mode='after')
    def times(self):
        if self.endedAt < self.startedAt: raise ValueError('Session ends before it starts')
        if self.entryMode == 'backdated' and self.historicalDate is None: raise ValueError('Historical date is required')
        if self.entryMode == 'live' and self.historicalDate is not None: raise ValueError('Live session cannot have a historical date')
        return self

class DrinkFields(Strict):
    category: Category
    name: str | None = Field(default=None, max_length=160)
    brand: str | None = Field(default=None, max_length=160)
    volumeMl: Volume
    abv: float = Field(ge=0, le=100, allow_inf_nan=False)

class Drink(Updated, DrinkFields):
    sessionId: Id
    alcoholMl: Finite
    alcoholGrams: Finite
    consumedAt: AwareDatetime

    @model_validator(mode='after')
    def quantities(self):
        # Allow historic rounding; reject values inconsistent with volume/ABV.
        ml=self.volumeMl*self.abv/100
        if abs(self.alcoholMl-ml)>0.02 or abs(self.alcoholGrams-ml*0.789)>0.02:
            raise ValueError('Alcohol quantities do not match volume and ABV')
        return self

class Water(Record):
    sessionId: Id
    loggedAt: AwareDatetime
    volumeMl: float | None = Field(default=None, gt=0, le=20000, allow_inf_nan=False)
    container: Literal['cup','bottle','custom'] | None = None
    containerLabel: str | None = Field(default=None,max_length=80)

class Break(Updated):
    sessionId: Id
    startedAt: AwareDatetime
    plannedEndAt: AwareDatetime
    endedAt: AwareDatetime | None = None
    plannedMinutes: float = Field(gt=0, le=1440, allow_inf_nan=False)
    status: Literal['active','completed','cancelled','interrupted']
    trigger: Literal['manual','paceSuggestion']
    interruptedByDrinkId: Id | None = None

    @model_validator(mode='after')
    def times(self):
        if self.plannedEndAt <= self.startedAt or (self.endedAt and self.endedAt < self.startedAt): raise ValueError('Invalid break times')
        if abs((self.plannedEndAt-self.startedAt).total_seconds()-self.plannedMinutes*60)>1: raise ValueError('Break duration mismatch')
        return self

class Bundle(Strict):
    id: Id
    session: Session
    drinks: list[Drink] = Field(max_length=2000)
    water: list[Water] = Field(max_length=2000)
    breaks: list[Break] = Field(max_length=2000)

    @model_validator(mode='after')
    def links(self):
        if self.id != self.session.id: raise ValueError('Session id mismatch')
        for items in (self.drinks,self.water,self.breaks):
            if len({i.id for i in items}) != len(items) or any(i.sessionId != self.id for i in items): raise ValueError('Invalid session child ownership')
        return self

class Favorite(Updated, DrinkFields):
    usageCount: int = Field(ge=0, le=2147483647)
    lastUsedAt: AwareDatetime | None = None

class Profile(Strict):
    id: Literal['default']
    ageConfirmed: bool
    weightKg: float | None = Field(default=None, ge=30, le=300, allow_inf_nan=False)
    onboardingCompleted: bool

    @model_validator(mode='after')
    def consent(self):
        if self.onboardingCompleted and (not self.ageConfirmed or self.weightKg is None): raise ValueError('Completed onboarding requires eligibility confirmation and weight')
        return self

SCHEMAS=dict(sessions=Bundle,favorites=Favorite,profile=Profile)

class Change(Strict):
    entity: Literal['sessions','favorites','profile']
    id: Id
    expected_version: int = Field(ge=0)
    data: dict | None

    @model_validator(mode='after')
    def data_shape(self):
        if self.entity=='profile' and self.id!='default': raise ValueError('Profile id must be default')
        if self.data is not None and SCHEMAS[self.entity].model_validate_json(json.dumps(self.data), strict=True).id != self.id: raise ValueError('Record id mismatch')
        return self

class Mutation(Strict):
    mutation_id: UUID
    changes: list[Change] = Field(min_length=1,max_length=100)

    @model_validator(mode='after')
    def keys_and_size(self):
        if len({(c.entity,c.id) for c in self.changes})!=len(self.changes): raise ValueError('Duplicate record key')
        if len(self.model_dump_json().encode())>4000000: raise ValueError('Alcohol batch exceeds 4 MB')
        return self
