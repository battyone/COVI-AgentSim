from enum import Enum, IntEnum, auto
import dataclasses
from typing import Union, Iterable, FrozenSet, Callable, List
from itertools import product
from collections import defaultdict
import numpy as np


class Severity(IntEnum):
    """
    Severity of the disease -- these should be adjectives.

    The pattern of numbers is not random: more severe adjectives should be assigned
    larger integers. This allows comparisons like:
    >>> Severity.MILD < Severity.SEVERE
    # Returns True
    """

    UNDEFINED = -1
    MILD = 0
    MODERATE = 1
    HEAVY = 2
    SEVERE = 3
    EXTREMELY_SEVERE = 4


class BaseSymptom(Enum):
    """
    Base symptoms the human can have. The pattern of numbers assigned to the
    various symptoms is random.
    """

    NO_SYMPTOMS = auto()
    FEVER = auto()
    CHILLS = auto()
    GASTRO = auto()
    DIARRHEA = auto()
    NAUSEA_VOMITTING = auto()
    FATIGUE = auto()
    UNUSUAL = auto()
    HARD_TIME_WAKING_UP = auto()
    HEADACHE = auto()
    CONFUSED = auto()
    LOST_CONSCIOUSNESS = auto()
    TROUBLE_BREATHING = auto()
    SNEEZING = auto()
    COUGH = auto()
    RUNNY_NOSE = auto()
    SORE_THROAT = auto()
    CHEST_PAIN = auto()
    LOSS_OF_TASTE = auto()
    ACHES = auto()


class DiseaseContext(IntEnum):
    """
    Phase (context?) of the disease. Supports comparisons, for instance:
        CovidContext.INCUBATION < CovidContext.ONSET evaluates to True.
        FluContext.FLU_FIRST_DAY < FluContext.FLU_LAST_DAY evaluates to True.
    """

    pass


class CovidContext(DiseaseContext):
    INCUBATION = 0
    ONSET = 1
    PLATEAU = 2
    POST_PLATEAU_1 = 3
    POST_PLATEAU_2 = 4


class AllergyContext(DiseaseContext):
    ALLERGY = 0


class ColdContext(DiseaseContext):
    COLD = 0
    COLD_LAST_DAY = 1


class FluContext(DiseaseContext):
    FLU_FIRST_DAY = 0
    FLU = 1
    FLU_LAST_DAY = 2


class Disease(Enum):
    COVID = CovidContext
    ALLERGY = AllergyContext
    COLD = ColdContext
    FLU = FluContext


@dataclasses.dataclass(unsafe_hash=True)
class Symptoms(object):
    """
    This class uniquely defines a symptom. A few gotchas:

    Comparisons with "==" work:
    >>> Symptoms(Severity.MILD, BaseSymptom.FEVER) == Symptoms(Severity.MILD, BaseSymptom.FEVER)
    # Returns True
    >>> Symptoms(Severity.SEVERE, BaseSymptom.FEVER) == Symptoms(Severity.MILD, BaseSymptom.FEVER)
    # Returns False (duh)

    You can print an autogenerated list of all possible symptoms:
    >>> for symptom in Symptoms.get_all_possible_symptoms():
    ...     print(symptom)
    This will work if you add more severity modes.
    """

    severity: Severity
    base_symptom: BaseSymptom

    @classmethod
    def get_all_possible_symptoms(cls):
        """Return a list of all possible symptoms."""
        return [
            Symptoms(severity, base_symptom)
            for severity, base_symptom in product(Severity, BaseSymptom)
        ]

    def __repr__(self):
        return f"Symptoms({self.severity.name}, {self.base_symptom.name})"

    def __str__(self):
        return f"{self.severity.name} {self.base_symptom.name}"

    @classmethod
    def make(cls, severity: str, base_symptom: str):
        severity_ = getattr(Severity, severity.upper(), None)
        if severity_ is None:
            raise ValueError(f"{severity} is not a valid Severity.")
        base_symptom_ = getattr(BaseSymptom, base_symptom.upper(), None)
        if base_symptom_ is None:
            raise ValueError(f"{base_symptom} is not a valid BaseSymptom.")
        return cls(severity=severity_, base_symptom=base_symptom_)


@dataclasses.dataclass(unsafe_hash=True, init=False)
class DiseasePhase(object):
    """
    This class uniquely defines a phase in the disease.

    The following works:
    >>> DiseasePhase(Disease.COVID, CovidContext.ONSET)
    The resulting object specifies the onset of COVID. The following throws an error:
    >>> DiseasePhase(Disease.COVID, ColdContext.COLD)
    AssertionError: Context COLD is not valid for disease COVID.
    """

    disease: Disease
    context: DiseaseContext

    def __init__(self, disease: Disease, context: DiseaseContext):
        super(DiseasePhase, self).__init__()
        self.disease = disease
        self.context = context
        assert (
            self.is_valid
        ), f"Context {context.name} is not valid for disease {disease.name}."

    @property
    def is_valid(self):
        return self.context in self.disease.value

    @classmethod
    def get_all_possible_disease_phases(cls):
        return [
            DiseasePhase(disease, context)
            for disease in Disease
            for context in Disease(disease).value
        ]

    def __str__(self):
        return f"{self.disease.name} ({self.context.name})"

    @classmethod
    def make(cls, disease: str, context: str):
        disease_ = getattr(Disease, disease.upper(), None)
        if disease_ is None:
            raise ValueError(f"{disease} is not a valid Disease.")
        context_ = getattr(Disease(disease_).value, context.upper(), None)
        if context_ is None:
            raise ValueError(f"{context} is not a valid context for disease {disease}")
        return cls(disease=disease_, context=context_)


@dataclasses.dataclass(unsafe_hash=True, init=False)
class HealthState(object):
    symptoms: FrozenSet[Symptoms]
    disease_phase: DiseasePhase

    def __init__(
        self,
        symptoms: Union[Symptoms, Iterable[Symptoms]],
        disease_phase: DiseasePhase,
    ):
        if isinstance(symptoms, Symptoms):
            self.symptoms = frozenset({symptoms})
        else:
            self.symptoms = frozenset(symptoms)
        self.disease_phase = disease_phase

    def __str__(self):
        if len(self.symptoms) == 1:
            symptom_description = str(next(iter(self.symptoms)))
        else:
            symptom_description = ", ".join([str(symptom) for symptom in self.symptoms])
        return f"{symptom_description} at {str(self.disease_phase)}"

    def __repr__(self):
        return f"HealthState({str(self)})"

    def issubset(self, other: Union["HealthState"]):
        # TODO
        raise NotImplementedError

    @classmethod
    def make(
        cls,
        severity: Union[str, List[str]],
        base_symptom: Union[str, List[str]],
        disease: str,
        context: str,
    ):
        severity = [severity] if isinstance(severity, str) else list(severity)
        base_symptom = (
            [base_symptom] if isinstance(base_symptom, str) else list(base_symptom)
        )
        if len(severity) == 1:
            severity *= max(len(severity), len(base_symptom))
        if len(base_symptom) == 1:
            base_symptom *= max(len(severity), len(base_symptom))
        symptoms = [
            Symptoms.make(severity=_severity, base_symptom=_base_symptom)
            for _severity, _base_symptom in zip(severity, base_symptom)
        ]
        disease_phase = DiseasePhase.make(disease=disease, context=context)
        return cls(symptoms=symptoms, disease_phase=disease_phase)

    @classmethod
    def parse(cls, desc: str):
        symptoms_desc, disease_desc = desc.split(" at ")
        all_symptom_desc = symptoms_desc.split(", ")
        parsed_symptom_descs = []
        for symptom_desc in all_symptom_desc:
            symptom_components = symptom_desc.split(" ")
            if len(symptom_components) == 2:
                parsed_symptom_descs.append(symptom_components)
            elif len(symptom_components) == 1:
                parsed_symptom_descs.append(["undefined", symptom_components[0]])
            else:
                raise ValueError
        severity, base_symptom = zip(*parsed_symptom_descs)
        disease, context = disease_desc.split(" ")
        return cls.make(severity, base_symptom, disease, context)


@dataclasses.dataclass
class TransitionRule(object):
    """
    Specifies one step in the progression of the disease together with its probability.
    """

    from_health_state: HealthState
    to_health_state: HealthState

    proba_score_value: float = None
    proba_fn: Union[Callable, None] = None
    proba_default: float = 0.0

    def get_proba(self, **proba_fn_kwargs) -> float:
        if self.proba_fn is not None:
            return self.proba_fn(self, **proba_fn_kwargs)
        elif self.proba_score_value is not None:
            return self.proba_score_value
        else:
            return self.proba_default

    def __hash__(self):
        return hash((self.from_health_state, self.to_health_state))

    def __str__(self):
        proba_str = (
            f"(P={self.proba_score_value})"
            if self.proba_score_value is not None
            else "(FN)"
            if self.proba_fn is not None
            else "(UNK)"
        )
        return f"{str(self.from_health_state)} --{proba_str}--> {str(self.to_health_state)}"


class TransitionRuleSet(object):
    # TODO Support for OR w.r.t symptoms of other states. For instance, one could
    #  have rules like:
    #   if current_health_state.symptom INTERSECT some_health_state.symptom is not empty:
    #       do this or that

    class WildCards(Enum):
        ALL_HEALTH_STATES = auto()
        ALL_SYMPTOMS = auto()
        ALL_DISEASE_PHASES = auto()

    def __init__(self):
        self.rule_set = defaultdict(set)

    def add_rule(self, transition_rule: TransitionRule):
        self.rule_set[transition_rule.from_health_state].add(transition_rule)
        return self

    def add_transition_rule(
        self,
        transition_rule: TransitionRule = None,
        from_health_state: Union[HealthState, WildCards] = None,
        to_health_state: Union[HealthState, WildCards] = None,
        from_symptoms: Union[Symptoms, Iterable[Symptoms], WildCards] = None,
        to_symptoms: Union[Symptoms, Iterable[Symptoms], WildCards] = None,
        at_disease_phase: Union[DiseasePhase, WildCards] = None,
        from_disease_phase: Union[DiseasePhase, WildCards] = None,
        to_disease_phase: Union[DiseasePhase, WildCards] = None,
        proba_score_value: float = None,
        proba_fn: Callable = None,
    ):
        # First priority goes to `transition_rule`, in the sense that only if it's not
        # provided, we dig deeper in to the other args.
        if transition_rule is None:
            # Second priority goes to health_states, but first a little excursion.
            if from_health_state is None or to_health_state is None:
                # First, we'll need to sort out what at_disease_phase is, because
                # it's shared between from_health_state and to_health_state
                at_disease_phase = self._validate_disease_phase(
                    at_disease_phase, allow_none=True
                )
            # Back to business -- second priority goes to health_states. Build a list
            if from_health_state is None:
                assert from_symptoms is not None, (
                    "Neither `transition_rule` nor `from_health_state` "
                    "is provided -- please provide `from_symptoms`."
                )

                from_symptoms: List[Symptoms] = self._validate_symptoms(from_symptoms)
                # if both `from_disease_phase` and `at_disease_phase` is provided,
                # priority goes to `from_disease_phase`.
                if from_disease_phase is None:
                    assert at_disease_phase is not None, (
                        "`from_disease_phase` is not provided -- please provide at "
                        "least `at_disease_phase` instead."
                    )
                    from_disease_phase = at_disease_phase
                else:
                    from_disease_phase = self._validate_disease_phase(
                        from_disease_phase, allow_none=False
                    )
                from_disease_phase: List[DiseasePhase]
                from_health_state = [
                    HealthState(symptoms=from_symptoms, disease_phase=disease_phase)
                    for disease_phase in from_disease_phase
                ]
            else:
                from_health_state = self._validate_health_state(from_health_state)
            from_health_state: List[HealthState]

            if to_health_state is None:
                assert to_symptoms is not None, (
                    "Neither `transition_rule` nor `to_health_state` "
                    "is provided -- please provide `to_symptoms.`"
                )
                to_symptoms: List[Symptoms] = self._validate_symptoms(to_symptoms)
                # if both `to_disease_phase` and `at_disease_phase` is provided,
                # priority goes to `to_disease_phase`.
                if to_disease_phase is None:
                    assert at_disease_phase is not None, (
                        "`to_disease_phase` is not provided -- please provide at "
                        "least `at_disease_phase` instead."
                    )
                else:
                    to_disease_phase = self._validate_disease_phase(
                        at_disease_phase, allow_none=False
                    )
                to_disease_phase: List[DiseasePhase]
                to_health_state = [
                    HealthState(symptoms=to_symptoms, disease_phase=disease_phase)
                    for disease_phase in to_disease_phase
                ]
            else:
                to_health_state = self._validate_health_state(to_health_state)
            to_health_state: List[HealthState]

            # Make a bunch of transition rules given all the to and from states
            transition_rule = [
                TransitionRule(
                    from_health_state=_from_health_state,
                    to_health_state=_to_health_state,
                    proba_score_value=proba_score_value,
                    proba_fn=proba_fn,
                )
                for _from_health_state, _to_health_state in product(
                    from_health_state, to_health_state
                )
            ]
        else:
            transition_rule = self._validate_transition_rule(transition_rule)
        transition_rule: List[TransitionRule]

        for _transition_rule in transition_rule:
            self.add_rule(transition_rule=_transition_rule)
        return self

    def sample_next_health_state(
        self,
        current_health_state: HealthState,
        rng: np.random.RandomState = np.random,
        **proba_fn_kwargs,
    ) -> HealthState:
        if current_health_state not in self.rule_set:
            raise ValueError(
                f"No forward rule defined for health-state {current_health_state}."
            )
        # Given the current state, pull all possible transition rules that tell
        # us what next state to go to, and compute the probability of going to the
        # said next state.
        candidate_next_health_states, next_state_probas = zip(
            *[
                (
                    transition_rule.to_health_state,
                    transition_rule.get_proba(**proba_fn_kwargs),
                )
                for transition_rule in self.rule_set[current_health_state]
            ]
        )
        # Make sure the next state probas sum to one?
        next_state_probas = np.array(next_state_probas)
        next_state_probas = next_state_probas / next_state_probas.sum()
        # Sample the next state
        next_health_state = rng.choice(
            candidate_next_health_states, p=next_state_probas
        )
        # ... and done.
        return next_health_state

    def _validate_disease_phase(self, disease_phase, allow_none=False):
        if disease_phase == self.WildCards.ALL_DISEASE_PHASES:
            disease_phase = DiseasePhase.get_all_possible_disease_phases()
        elif isinstance(disease_phase, Iterable):
            disease_phase = list(disease_phase)
        elif isinstance(disease_phase, DiseasePhase):
            disease_phase = [disease_phase]
        else:
            if allow_none:
                assert disease_phase is None, (
                    f"`disease_phase` can be a wildcard (instance of "
                    f"TransitionRuleSet.WildCard), an iterable, an instance "
                    f"of DiseasePhase or None. Got type {type(disease_phase)} "
                    f"instead."
                )
            else:
                raise TypeError(
                    f"`disease_phase` can be a wildcard (instance of "
                    f"TransitionRuleSet.WildCard), an iterable, an instance "
                    f"of DiseasePhase. Got type {type(disease_phase)} "
                    f"instead."
                )
        assert all(
            [isinstance(dp, DiseasePhase) for dp in disease_phase]
        ), "`disease_phase` is not an iterable of `DiseasePhase` instances."
        return disease_phase

    def _validate_symptoms(self, symptoms):
        if symptoms == self.WildCards.ALL_SYMPTOMS:
            symptoms = Symptoms.get_all_possible_symptoms()
        elif isinstance(symptoms, Iterable):
            symptoms = list(symptoms)
        elif isinstance(symptoms, Symptoms):
            symptoms = [symptoms]
        else:
            raise TypeError(
                f"`symptoms` should be one of: iterable, "
                f"`Symptoms` instance or a TransitionRuleSet.WildCard. "
                f"Got an instance of {type(symptoms)} instead."
            )
        assert all(
            [isinstance(s, Symptoms) for s in symptoms]
        ), "`symptoms` is not an iterable of Symptoms instances."
        return symptoms

    # noinspection PyMethodMayBeStatic
    def _validate_health_state(self, health_state):
        if isinstance(health_state, Iterable):
            health_state = list(health_state)
        elif isinstance(health_state, HealthState):
            health_state = [health_state]
        else:
            raise TypeError(
                f"`health_state` must be an instance of HealthState "
                f"or an iterable of HealthState instances. Got "
                f"{type(health_state)} instead."
            )
        assert all(
            [isinstance(hs, HealthState) for hs in health_state]
        ), "`health_state` is not an iterable of HealthState instances."
        return health_state

    # noinspection PyMethodMayBeStatic
    def _validate_transition_rule(self, transition_rule):
        if isinstance(transition_rule, Iterable):
            transition_rule = list(transition_rule)
        elif isinstance(transition_rule, TransitionRule):
            transition_rule = [transition_rule]
        else:
            raise TypeError(
                f"`transition_rule` must be an instance of `TransitionRule` "
                f"or an iterable of `TransitionRule` instances. Got "
                f"{type(transition_rule)} instead."
            )
        assert all(
            [isinstance(tr, TransitionRule) for tr in transition_rule]
        ), "`transition_rule` is not an iterable of TransitionRule instances."
        return transition_rule


if __name__ == "__main__":
    default_rules = TransitionRuleSet()
    default_rules.add_transition_rule(
        from_health_state=HealthState.parse("mild fever at covid onset"),
        to_health_state=HealthState.parse("moderate fever at covid onset"),
        proba_score_value=0.5,
    )
    default_rules.add_transition_rule(
        from_health_state=HealthState.parse("mild fever at covid onset"),
        to_health_state=HealthState.parse("severe fever, headache at covid onset"),
        proba_score_value=0.5,
    )
    print(
        default_rules.sample_next_health_state(
            current_health_state=HealthState.parse("mild fever at covid onset")
        )
    )
    # Prints either with proba 0.5:
    #   SEVERE FEVER, UNDEFINED HEADACHE at COVID (ONSET)
    #   MODERATE FEVER at COVID (ONSET)

# TODO:
#  * Ensure that transitions cannot happen from higher phase to lower phases
#  * Export to networkx graph (visualization)
#  * Pretty printing
#  * Parse ruleset from a text file
