"""

Tracing is a logic engine for non-ml contact tracing methods

"""
import datetime
import typing
import numpy as np

from covid19sim.constants import BIG_NUMBER
from covid19sim.interventions import RiskBasedRecommendations, HeuristicRecommendations, BinaryTracing
if typing.TYPE_CHECKING:
    from covid19sim.city import PersonalMailboxType

class Tracing(object):
    """
    Implements tracing. Assigns risk_levels to Humans.

    This object carries a bunch of flags & is responsible for determining the risk level of humans when
    the transformer is not used for risk level inference. To do so, it will use the targeted human's
    contact book to pull statistics about its recent contacts.

    If the transformer is used, this object becomes fairly useless, and will only be used to apply
    recommended behavior changes.

    The name of this class is probably not the best, feel free to suggest alternatives.

    Attributes:
        risk_model (str): type of tracing to use. The following methods are currently
            available: digital, manual, naive, other, transformer.
        p_contact (float): adds a noise to the tracing procedure, as it is not always possible
            to contact everyone (or remember all contacts) when using manual tracing.
        delay (int): defines whether there should be a delay between the time when someone
            triggers tracing and someone is traced. It is 0 for digital tracing, and 1 for manual.
        app (bool): defines whether an app is required for this tracing. For example, manual
            tracing doesn't use app.
        max_depth (int, optional): The number of hops away from the source to consider while tracing.
            The term `order` is also used for this. Defaults to 1.
        propagate_symptoms (bool, optional): Defines whether tracing is to be triggered when someone
            reports symptoms. Defaults to False.
        propagate_risk (bool, optional): Define whether tracing is to be triggered when someone
            changes their risk level. Defaults to False. Note: this is not to be mixed with
            risk_model="transformer".
        should_modify_behavior (bool, optional): Defines whether behavior should be modified or not
            following the tracing intervention for conunterfactual studies. Defaults to True.

    """
    def __init__(self, conf: dict):
        """
        Initializes the tracing object.

        Args:
            conf (dict): configuration to parse settings from.
        """
        risk_model = conf.get("RISK_MODEL")
        max_depth = conf.get("TRACING_ORDER")
        symptoms = conf.get("TRACE_SYMPTOMS")
        risk = conf.get("TRACE_RISK_UPDATE")
        should_modify_behavior = conf.get("SHOULD_MODIFY_BEHAVIOR"),

        self.risk_model = risk_model
        if risk_model in ['manual', 'digital']:
            self.intervention = BinaryTracing()
        elif risk_model == "heuristicv1":
            self.intervention = HeuristicRecommendations(version=1, conf=conf)
        elif risk_model == "heuristicv2":
            self.intervention = HeuristicRecommendations(version=2, conf=conf)
        else:
            # risk based
            self.intervention = RiskBasedRecommendations()

        self.max_depth = max_depth
        self.propagate_symptoms = symptoms
        self.propagate_risk = risk
        self.propagate_postive_test = True  # bare minimum
        self.should_modify_behavior = should_modify_behavior

        self.p_contact = 1
        self.delay = 0
        self.app = True
        if risk_model == "manual":
            assert not symptoms, "makes no sense to trace symptoms by phone...?"
            assert not risk, "don't make be believe we will trace risk by phone either"
            self.p_contact = conf.get("MANUAL_TRACING_P_CONTACT")
            self.delay = 1
            self.app = False

        self.propagate_risk_max_depth = max_depth
        # more than 3 will slow down the simulation too much
        if self.propagate_risk:
            self.propage_risk_max_depth = min(3, max_depth)

        if risk_model == "transformer":
            self.propagate_risk_max_depth = BIG_NUMBER
            self.propagate_risk = False
            self.propagate_symptoms = False

    # Mirror BehaviorInterventions interface
    def get_recommendations(self, human: "Human"):
        recommendations = []
        if self.should_modify_behavior:
            recommendations = self.intervention.get_recommendations(human)
        return recommendations

    # Mirror BehaviorInterventions interface
    def revert_behavior(self, human):
        self.intervention.revert_behavior(human)

    def _get_hypothetical_contact_tracing_results(
            self,
            human: "Human",
            mailbox: "PersonalMailboxType",
            humans_map: typing.Dict[str, "Human"],
    ) -> typing.Tuple[int, int, typing.Tuple[int, int, int, int]]:
        """
        Returns the counts for the 'hypothetical' tracing methods that might be used in apps/real life.

        This function will use the target human's logged encounters to fetch all his contacts using the
        provided city-wide human map. The number of past days covered by the tracing will depend on the
        contact book's maximum history, which should be defined from `TRACING_N_DAYS_HISTORY`.

        Args:
            human: the human for which to generate the contact tracing counts.
            mailbox: centralized mailbox with all recent update messages for the target human.
            humans_map: a human-name-to-human-object reference map to pass to the contact book functions.

        Returns:
            t (int): Number of recent contacts that are tested positive.
            s (int): Number of recent contacts that have reported symptoms.
                r_up: Number of recent contacts that increased their risk levels.
                v_up: Average increase in magnitude of risk levels of recent contacts.
                r_down: Number of recent contacts that decreased their risk levels.
                v_down: Average decrease in magnitude of risk levels of recent contacts.
        """
        assert self.risk_model != "transformer", "we should never be in here!"
        assert self.risk_model in ["manual", "digital", "naive", "heuristicv1", "heuristicv2", "other"], "missing something?"
        t, s, r_up, r_down, v_up, v_down = 0, 0, 0, 0, 0, 0

        if self.risk_model == "manual":
            # test_tracing_delay = datetime.timedelta(days=1)  # 1 day was previously used by default
            raise NotImplementedError(  # TODO: complete implementation as detailed below
                "the current implementation does not log encounters if the users do not have the app; "
                "therefore, manual tracing is dead --- we could fix that by logging encounters all the "
                "time (with a global flab?) and by checking that flag in the tracing call below as well"
                # ... or by simply assuming everyone has an app?
            )
        else:
            test_tracing_delay = datetime.timedelta(days=0)
        positive_test_counts = human.contact_book.get_positive_contacts_counts(
            humans_map=humans_map,
            tracing_delay=test_tracing_delay,
            tracing_probability=self.p_contact,
            max_order=self.max_depth,
            make_sure_15min_minimum_between_contacts=False,
        )
        for order, count in positive_test_counts.items():
            t += count * np.exp(-2*(order-1))

        if self.propagate_symptoms:
            symptomatic_counts = human.contact_book.get_symptomatic_contacts_counts(
                humans_map=humans_map, max_order=self.max_depth)
            for order, count in symptomatic_counts.items():
                s += count * np.exp(-2*(order-1))

        if self.propagate_risk:
            # TODO: contact book is still missing the r_up,r_down,v_up,v_down tracing functions
            # note1: we could use the simpler `get_risk_level_update_counts` function instead?
            # note2: for whoever might want to reimplement the missing tracing, check the orig code
            # note3: the mailbox is passed into this function, we could give it to the contact book
            #        (or to a pure function from somewhere else) to fetch the 4 counts
            raise NotImplementedError
        return t, s, (r_up, v_up, r_down, v_down)

    def compute_risk(
            self,
            human: "Human",
            mailbox: "PersonalMailboxType",
            humans_map: typing.Dict[str, "Human"],
    ):
        """
        Computes the infection risk of a human based on the statistics of its past contacts.

        Args:
            human: the human for which to generate the contact tracing counts.
            mailbox: centralized mailbox with all recent update messages for the target human.
            humans_map: a human-name-to-human-object reference map to pass to the contact book functions.

        Returns:
            float: a scalar value.
        """
        assert self.risk_model != "transformer", "we should never be in here!"
        assert self.risk_model in ["manual", "digital", "naive", "heuristicv1", "heuristicv2", "other"], "missing something?"
        if self.risk_model in ['manual', 'digital']:
            t, s, r = self._get_hypothetical_contact_tracing_results(human, mailbox, humans_map)
            if t + s > 0:
                risk = 1.0
            else:
                risk = 0.0

        elif self.risk_model == "naive":
            risk = 1.0 - (1.0 - human.conf.get("RISK_TRANSMISSION_PROBA")) ** (t+s)

        elif self.risk_model in ["heuristicv1", "heuristicv2"]:
            risk = self.intervention.compute_risk(human, mailbox)

        elif self.risk_model == "other":
            r_up, v_up, r_down, v_down = r
            r_score = 2*v_up - v_down
            risk = 1.0 - (1.0 - human.conf.get("RISK_TRANSMISSION_PROBA")) ** (t + 0.5*s + r_score)

        return risk if isinstance(risk, list) else [risk]

    def compute_tracing_delay(self, human):
        """
        Computes delay for tracing. NOT IMPLEMENTED.

        Args:
            human (Human): `Human` object
        """
        pass # FIXME: circualr imports issue; can't import _draw_random_discreet_gaussian

    def __repr__(self):
        if self.risk_model == "transformer":
            return f"Tracing: {self.risk_model}"
        return f"Tracing: {self.risk_model} order {self.max_depth} symptoms: {self.propagate_symptoms} risk: {self.propagate_risk} modify:{self.should_modify_behavior}"

