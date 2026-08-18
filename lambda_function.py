import json
import os
import random
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key


TABLE_NAME = os.environ.get(
    "TABLE_NAME",
    "lovely-system-disclaimer",
)

QUESTION_COOLDOWN_DAYS = int(
    os.environ.get(
        "QUESTION_COOLDOWN_DAYS",
        "30",
    )
)

DOMAIN_SIZE = 20


dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


SEED_QUESTIONS = [
    {
        "id": "opening-1",
        "interaction": "yes_no",
        "text":
            "You agree to provide accurate information when information is requested.",
        "authored_absurdity": 2,
    },
    {
        "id": "opening-2",
        "interaction": "yes_no",
        "text":
            "You agree not to interfere with the normal operation of the system.",
        "authored_absurdity": 2,
    },
    {
        "id": "opening-3",
        "interaction": "yes_no",
        "text":
            "You agree to treat other users with reasonable consideration.",
        "authored_absurdity": 3,
    },
    {
        "id": "q-001",
        "interaction": "agree_disagree",
        "text":
            "You agree to keep information you provide reasonably current.",
        "authored_absurdity": 4,
    },
    {
        "id": "q-002",
        "interaction": "true_false",
        "text":
            "Users should make reasonable efforts to protect their account information.",
        "authored_absurdity": 5,
    },
    {
        "id": "q-003",
        "interaction": "yes_no",
        "text":
            "Do you agree not to attempt unauthorized access to restricted portions of the system?",
        "authored_absurdity": 4,
    },
    {
        "id": "q-004",
        "interaction": "true_false_decline",
        "text":
            "Service availability may occasionally be interrupted for maintenance.",
        "authored_absurdity": 6,
    },
    {
        "id": "q-020",
        "interaction": "agree_disagree",
        "text":
            "You agree to exercise reasonable judgment when determining whether reasonable judgment is required.",
        "authored_absurdity": 28,
    },
    {
        "id": "q-021",
        "interaction": "yes_no",
        "text":
            "Do you agree to notify the system if your understanding of a previous acknowledgment materially changes?",
        "authored_absurdity": 25,
    },
    {
        "id": "q-022",
        "interaction": "multiple_choice",
        "text":
            "Who is primarily responsible for ensuring that you understand these terms?",
        "choices": [
            "You",
            "Your authorized representative",
            "You and your authorized representative",
            "Other",
            "Our Lovely System",
        ],
        "authored_absurdity": 31,
    },
    {
        "id": "q-023",
        "interaction": "fill_blank",
        "text":
            "The person primarily responsible for my actions is ______.",
        "authored_absurdity": 34,
    },
    {
        "id": "q-040",
        "interaction": "agree_disagree",
        "text":
            "You acknowledge that acknowledgment of a condition does not necessarily imply that the condition required acknowledgment.",
        "authored_absurdity": 47,
    },
    {
        "id": "q-041",
        "interaction": "yes_no",
        "text":
            "Do you agree not to knowingly misrepresent whether you knew something at the time you represented that you knew it?",
        "authored_absurdity": 49,
    },
    {
        "id": "q-042",
        "interaction": "true_false_decline",
        "text":
            "A reasonable person can generally determine when another reasonable person is being unreasonable.",
        "authored_absurdity": 52,
    },
    {
        "id": "q-060",
        "interaction": "yes_no",
        "text":
            "Do you agree not to introduce livestock into system facilities without first determining whether the livestock has legitimate business there?",
        "authored_absurdity": 68,
    },
    {
        "id": "q-061",
        "interaction": "agree_disagree",
        "text":
            "You acknowledge that objects described as temporary may remain temporary for an indefinite period.",
        "authored_absurdity": 63,
    },
    {
        "id": "q-062",
        "interaction": "multiple_choice",
        "text":
            "If an unauthorized animal presents credentials, what should you do?",
        "choices": [
            "Verify the credentials",
            "Notify an authorized representative",
            "Ask the animal to wait",
            "Use reasonable judgment",
            "None of the above",
        ],
        "authored_absurdity": 72,
    },
    {
        "id": "q-080",
        "interaction": "agree_disagree",
        "text":
            "You agree not to impersonate an authorized representative unless you are an authorized representative engaged in an authorized impersonation.",
        "authored_absurdity": 82,
    },
    {
        "id": "q-081",
        "interaction": "yes_no",
        "text":
            "Do you agree that not every chair encountered during use of the system is necessarily intended for sitting?",
        "authored_absurdity": 85,
    },
    {
        "id": "q-082",
        "interaction": "fill_blank",
        "text":
            "In the event of a dispute involving a goose, the first person I would contact is ______.",
        "authored_absurdity": 91,
    },
    {
        "id": "q-083",
        "interaction": "true_false_decline",
        "text":
            "A sandwich left unattended for more than twenty minutes may reasonably be considered abandoned.",
        "authored_absurdity": 94,
    },
]


AFFIRMATIVE = {
    "yes",
    "agree",
    "true",
}

REFUSAL = {
    "no",
    "disagree",
    "false",
    "decline",
    "decline to answer",
}

VALID_INTERACTIONS = {
    "yes_no",
    "agree_disagree",
    "true_false",
    "true_false_decline",
    "multiple_choice",
    "fill_blank",
    "free_response",
}


def utc_now():
    return datetime.now(timezone.utc)


def ts(value=None):
    return (
        (value or utc_now())
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def reply(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            "Cache-Control": "no-store",
        },
        "body": json.dumps(
            body,
            default=lambda value:
                float(value)
                if isinstance(value, Decimal)
                else str(value),
        ),
    }


def parse_body(event):
    raw = event.get("body")

    if not raw:
        return {}

    if isinstance(raw, dict):
        return raw

    value = json.loads(raw)

    if not isinstance(value, dict):
        raise ValueError(
            "request body must be an object"
        )

    return value


def participant_pk(pid):
    return f"PARTICIPANT#{pid}"


def session_sk(sid):
    return f"SESSION#{sid}"


def presentation_sk(qid):
    return f"PRESENTED#{qid}"


def question_pk(qid):
    return f"QUESTION#{qid}"


def absurdity_domain(value):
    number = max(
        0,
        min(
            100,
            int(float(value)),
        ),
    )

    lower = (
        number // DOMAIN_SIZE
    ) * DOMAIN_SIZE

    if lower == 100:
        lower = 80

    upper = min(
        100,
        lower + DOMAIN_SIZE - 1,
    )

    return f"{lower}-{upper}"


def get_item(
    pk_value,
    sk_value,
):
    return table.get_item(
        Key={
            "pk": pk_value,
            "sk": sk_value,
        },
        ConsistentRead=True,
    ).get("Item")


def scan_all():
    items = []
    kwargs = {}

    while True:

        result = table.scan(
            **kwargs
        )

        items.extend(
            result.get(
                "Items",
                [],
            )
        )

        last = result.get(
            "LastEvaluatedKey"
        )

        if not last:
            break

        kwargs[
            "ExclusiveStartKey"
        ] = last

    return items


def get_participant(pid):
    return get_item(
        participant_pk(pid),
        "META",
    )


def require_participant(pid):
    item = get_participant(pid)

    if not item:
        raise LookupError(
            "participant not found"
        )

    return item


def put_participant(item):
    table.put_item(
        Item=item
    )


def get_session(
    pid,
    sid,
):
    return get_item(
        participant_pk(pid),
        session_sk(sid),
    )


def get_or_create_session(
    pid,
    sid,
):
    item = get_session(
        pid,
        sid,
    )

    if item:
        return item

    item = {
        "pk":
            participant_pk(pid),

        "sk":
            session_sk(sid),

        "record_type":
            "session",

        "participant_id":
            pid,

        "session_id":
            sid,

        "created_at":
            ts(),

        "locked_domains":
            [],

        "domain_yes_counts":
            {},
    }

    table.put_item(
        Item=item
    )

    return item


def save_session(item):
    table.put_item(
        Item=item
    )


def migrate_existing_seed_questions():

    for seed in SEED_QUESTIONS:

        item = get_item(
            question_pk(
                seed["id"]
            ),
            "META",
        )

        if not item:
            continue

        changed = False

        defaults = {
            "record_type":
                "question",

            "question_id":
                seed["id"],

            "text":
                seed["text"],

            "interaction":
                seed["interaction"],

            "choices":
                seed.get(
                    "choices",
                    [],
                ),

            "active":
                True,

            "created_by":
                "system",
        }

        for key, value in (
            defaults.items()
        ):

            if key not in item:

                item[key] = value

                changed = True

        if changed:

            item[
                "migrated_at"
            ] = ts()

            table.put_item(
                Item=item
            )


def all_questions(
    active_only=True,
):
    migrate_existing_seed_questions()

    questions = [
        item
        for item
        in scan_all()
        if item.get(
            "record_type"
        ) == "question"
    ]

    if active_only:

        questions = [
            item
            for item
            in questions
            if item.get(
                "active",
                True,
            )
        ]

    return questions


def question_by_id(qid):

    migrate_existing_seed_questions()

    return get_item(
        question_pk(qid),
        "META",
    )


def serialize_question(
    question,
):
    result = {
        "question_id":
            question[
                "question_id"
            ],

        "interaction":
            question[
                "interaction"
            ],

        "text":
            question[
                "text"
            ],

        "authored_absurdity":
            float(
                question[
                    "authored_absurdity"
                ]
            ),

        "observed_absurdity":
            float(
                question[
                    "observed_absurdity"
                ]
            ),

        "created_by":
            question.get(
                "created_by",
                "system",
            ),
    }

    if question.get(
        "choices"
    ):
        result[
            "choices"
        ] = question[
            "choices"
        ]

    return result


def adjust_absurdity(
    qid,
    direction,
):
    question = question_by_id(
        qid
    )

    if not question:
        return

    current = Decimal(
        str(
            question[
                "observed_absurdity"
            ]
        )
    )

    if direction == "up":

        current += Decimal(
            "0.1"
        )

        question[
            "no_count"
        ] = (
            int(
                question.get(
                    "no_count",
                    0,
                )
            )
            + 1
        )

    elif direction == "down":

        current -= Decimal(
            "0.1"
        )

        question[
            "yes_count"
        ] = (
            int(
                question.get(
                    "yes_count",
                    0,
                )
            )
            + 1
        )

    question[
        "observed_absurdity"
    ] = max(
        Decimal("0"),
        min(
            Decimal("100"),
            current,
        ),
    )

    question[
        "updated_at"
    ] = ts()

    table.put_item(
        Item=question
    )


def get_presentation(
    pid,
    qid,
):
    return get_item(
        participant_pk(pid),
        presentation_sk(qid),
    )


def record_presentation(
    pid,
    qid,
):
    now = utc_now()

    table.put_item(
        Item={
            "pk":
                participant_pk(pid),

            "sk":
                presentation_sk(qid),

            "record_type":
                "presentation",

            "participant_id":
                pid,

            "question_id":
                qid,

            "last_presented_at":
                ts(now),

            "eligible_again_at":
                ts(
                    now
                    +
                    timedelta(
                        days=
                            QUESTION_COOLDOWN_DAYS
                    )
                ),
        }
    )


def cooling_down(
    pid,
    qid,
):
    item = get_presentation(
        pid,
        qid,
    )

    if not item:
        return False

    eligible_text = item.get(
        "eligible_again_at"
    )

    if not eligible_text:
        return False

    eligible_at = (
        datetime.fromisoformat(
            eligible_text.replace(
                "Z",
                "+00:00",
            )
        )
    )

    return utc_now() < eligible_at


def create_participant(data):

    name = str(
        data.get(
            "declared_name",
            "",
        )
    ).strip()

    if not name:

        return reply(
            400,
            {
                "error":
                    "declared_name is required"
            },
        )

    pid = str(
        uuid.uuid4()
    )

    item = {
        "pk":
            participant_pk(pid),

        "sk":
            "META",

        "record_type":
            "participant",

        "participant_id":
            pid,

        "declared_name":
            name[:200],

        "created_at":
            ts(),

        "question_count":
            0,

        "affirmative_count":
            0,

        "refusal_count":
            0,

        "yes_man_eligible":
            True,

        "yes_man_qualified":
            False,

        "troublemaker_qualified":
            False,

        "target_absurdity":
            Decimal("5"),
    }

    put_participant(
        item
    )

    return reply(
        201,
        {
            "participant_id":
                pid,

            "declared_name":
                name,
        },
    )


def classify(
    interaction,
    value,
):

    normalized = (
        str(value)
        .strip()
        .lower()
    )

    if interaction in {
        "multiple_choice",
        "fill_blank",
        "free_response",
    }:
        return "neutral"

    if normalized in AFFIRMATIVE:
        return "affirmative"

    if normalized in REFUSAL:
        return "refusal"

    return "neutral"


def all_domains(
    questions,
):

    return sorted(
        {
            absurdity_domain(
                question[
                    "observed_absurdity"
                ]
            )
            for question
            in questions
        },
        key=lambda domain:
            int(
                domain.split("-")[0]
            ),
    )


def eligible_in_domain(
    pid,
    domain,
    questions,
):

    return [
        question
        for question
        in questions
        if
        absurdity_domain(
            question[
                "observed_absurdity"
            ]
        ) == domain
        and
        not cooling_down(
            pid,
            question[
                "question_id"
            ],
        )
    ]


def nearest_open_domain(
    pid,
    session,
    target,
    questions,
):

    locked = set(
        session.get(
            "locked_domains",
            [],
        )
    )

    possible = []

    for domain in all_domains(
        questions
    ):

        if domain in locked:
            continue

        eligible = (
            eligible_in_domain(
                pid,
                domain,
                questions,
            )
        )

        if not eligible:

            locked.add(
                domain
            )

            continue

        lower, upper = [
            int(value)
            for value
            in domain.split("-")
        ]

        midpoint = (
            lower + upper
        ) / 2

        possible.append(
            (
                abs(
                    midpoint
                    - float(target)
                ),
                domain,
                eligible,
            )
        )

    session[
        "locked_domains"
    ] = sorted(
        locked
    )

    save_session(
        session
    )

    if not possible:
        return None, []

    possible.sort(
        key=lambda item:
            item[0]
    )

    return (
        possible[0][1],
        possible[0][2],
    )


def qualify_finisher(
    participant,
):

    if participant.get(
        "yes_man_eligible",
        True,
    ):

        participant[
            "yes_man_qualified"
        ] = True

        participant[
            "troublemaker_qualified"
        ] = False

        destination = (
            "yes-man"
        )

    else:

        participant[
            "yes_man_qualified"
        ] = False

        participant[
            "troublemaker_qualified"
        ] = True

        destination = (
            "troublemaker"
        )

    participant[
        "completed_at"
    ] = ts()

    put_participant(
        participant
    )

    return destination


def next_question(
    pid,
    sid,
):

    participant = (
        require_participant(
            pid
        )
    )

    session = (
        get_or_create_session(
            pid,
            sid,
        )
    )

    questions = (
        all_questions(
            active_only=True
        )
    )

    if not questions:

        return reply(
            200,
            {
                "complete":
                    True,

                "destination":
                    "empty",

                "reason":
                    "question_pool_empty",
            },
        )

    count = int(
        participant.get(
            "question_count",
            0,
        )
    )

    if count < 3:

        opening_id = (
            f"opening-{count + 1}"
        )

        opening = next(
            (
                question
                for question
                in questions
                if question.get(
                    "question_id"
                ) == opening_id
            ),
            None,
        )

        if (
            opening
            and
            not cooling_down(
                pid,
                opening_id,
            )
        ):

            record_presentation(
                pid,
                opening_id,
            )

            return reply(
                200,
                {
                    "complete":
                        False,

                    "question":
                        serialize_question(
                            opening
                        ),

                    "domain":
                        absurdity_domain(
                            opening[
                                "observed_absurdity"
                            ]
                        ),

                    "locked_domains":
                        session.get(
                            "locked_domains",
                            [],
                        ),
                },
            )

    target = Decimal(
        str(
            participant.get(
                "target_absurdity",
                5,
            )
        )
    )

    domain, eligible = (
        nearest_open_domain(
            pid,
            session,
            target,
            questions,
        )
    )

    if not eligible:

        destination = (
            qualify_finisher(
                participant
            )
        )

        return reply(
            200,
            {
                "complete":
                    True,

                "destination":
                    destination,

                "reason":
                    "no_eligible_questions",
            },
        )

    question = random.choice(
        eligible
    )

    record_presentation(
        pid,
        question[
            "question_id"
        ],
    )

    return reply(
        200,
        {
            "complete":
                False,

            "question":
                serialize_question(
                    question
                ),

            "domain":
                domain,

            "locked_domains":
                session.get(
                    "locked_domains",
                    [],
                ),
        },
    )


def answer_question(
    pid,
    sid,
    data,
):

    participant = (
        require_participant(
            pid
        )
    )

    session = (
        get_or_create_session(
            pid,
            sid,
        )
    )

    qid = str(
        data.get(
            "question_id",
            "",
        )
    )

    question = question_by_id(
        qid
    )

    if (
        not question
        or
        not question.get(
            "active",
            True,
        )
    ):
        return reply(
            400,
            {
                "error":
                    "unknown question"
            },
        )

    value = data.get(
        "response",
        "",
    )

    classification = classify(
        question[
            "interaction"
        ],
        value,
    )

    domain = absurdity_domain(
        question[
            "observed_absurdity"
        ]
    )

    event_id = str(
        uuid.uuid4()
    )

    created_at = ts()

    table.put_item(
        Item={
            "pk":
                participant_pk(pid),

            "sk":
                f"EVENT#{created_at}#{event_id}",

            "record_type":
                "response",

            "event_id":
                event_id,

            "participant_id":
                pid,

            "session_id":
                sid,

            "question_id":
                qid,

            "interaction":
                question[
                    "interaction"
                ],

            "presented_text":
                question[
                    "text"
                ],

            "choices":
                question.get(
                    "choices",
                    [],
                ),

            "response":
                str(value),

            "classification":
                classification,

            "domain":
                domain,

            "authored_absurdity":
                question[
                    "authored_absurdity"
                ],

            "observed_absurdity_at_time":
                question[
                    "observed_absurdity"
                ],

            "created_at":
                created_at,
        }
    )

    participant[
        "question_count"
    ] = (
        int(
            participant.get(
                "question_count",
                0,
            )
        )
        + 1
    )

    target = Decimal(
        str(
            participant.get(
                "target_absurdity",
                5,
            )
        )
    )

    followup = None

    if classification == (
        "affirmative"
    ):

        participant[
            "affirmative_count"
        ] = (
            int(
                participant.get(
                    "affirmative_count",
                    0,
                )
            )
            + 1
        )

        adjust_absurdity(
            qid,
            "down",
        )

        target += Decimal(
            "6"
        )

        counts = dict(
            session.get(
                "domain_yes_counts",
                {},
            )
        )

        counts[
            domain
        ] = (
            int(
                counts.get(
                    domain,
                    0,
                )
            )
            + 1
        )

        session[
            "domain_yes_counts"
        ] = counts

        if (
            counts[
                domain
            ]
            >= 3
        ):

            locked = set(
                session.get(
                    "locked_domains",
                    [],
                )
            )

            locked.add(
                domain
            )

            session[
                "locked_domains"
            ] = sorted(
                locked
            )

    elif classification == (
        "refusal"
    ):

        participant[
            "refusal_count"
        ] = (
            int(
                participant.get(
                    "refusal_count",
                    0,
                )
            )
            + 1
        )

        participant[
            "yes_man_eligible"
        ] = False

        adjust_absurdity(
            qid,
            "up",
        )

        target -= Decimal(
            "10"
        )

        roll = random.random()

        if roll < 0.30:

            followup = {
                "type":
                    "why_not",

                "text":
                    "Why not?",

                "related_event_id":
                    event_id,
            }

        elif roll < 0.45:

            followup = {
                "type":
                    "would_you",

                "text":
                    random.choice(
                        [
                            "Would you agree to it in a box?",
                            "Would you agree to it while wearing socks?",
                            "Would you agree to it somewhere else?",
                        ]
                    ),

                "related_event_id":
                    event_id,
            }

    participant[
        "target_absurdity"
    ] = max(
        Decimal("0"),
        min(
            Decimal("100"),
            target,
        ),
    )

    put_participant(
        participant
    )

    save_session(
        session
    )

    return reply(
        201,
        {
            "event_id":
                event_id,

            "classification":
                classification,

            "followup":
                followup,

            "domain":
                domain,

            "domain_locked":
                domain
                in session.get(
                    "locked_domains",
                    [],
                ),

            "target_absurdity":
                float(
                    participant[
                        "target_absurdity"
                    ]
                ),
        },
    )


def record_followup(
    pid,
    sid,
    data,
):

    require_participant(
        pid
    )

    event_id = str(
        uuid.uuid4()
    )

    created_at = ts()

    table.put_item(
        Item={
            "pk":
                participant_pk(pid),

            "sk":
                f"EVENT#{created_at}#{event_id}",

            "record_type":
                "followup",

            "event_id":
                event_id,

            "participant_id":
                pid,

            "session_id":
                sid,

            "followup_type":
                str(
                    data.get(
                        "followup_type",
                        "",
                    )
                ),

            "presented_text":
                str(
                    data.get(
                        "presented_text",
                        "",
                    )
                ),

            "response":
                str(
                    data.get(
                        "response",
                        "",
                    )
                ),

            "related_event_id":
                str(
                    data.get(
                        "related_event_id",
                        "",
                    )
                ),

            "created_at":
                created_at,
        }
    )

    return reply(
        201,
        {
            "event_id":
                event_id
        },
    )


def participant_record(pid):

    participant = (
        require_participant(
            pid
        )
    )

    result = table.query(
        KeyConditionExpression=(
            Key("pk").eq(
                participant_pk(pid)
            )
            &
            Key("sk").begins_with(
                "EVENT#"
            )
        ),
        ConsistentRead=True,
    )

    return reply(
        200,
        {
            "participant": {
                "participant_id":
                    pid,

                "declared_name":
                    participant.get(
                        "declared_name",
                        "",
                    ),

                "created_at":
                    participant.get(
                        "created_at",
                        "",
                    ),
            },

            "summary": {
                "question_count":
                    int(
                        participant.get(
                            "question_count",
                            0,
                        )
                    ),

                "affirmative_count":
                    int(
                        participant.get(
                            "affirmative_count",
                            0,
                        )
                    ),

                "refusal_count":
                    int(
                        participant.get(
                            "refusal_count",
                            0,
                        )
                    ),

                "yes_man_eligible":
                    bool(
                        participant.get(
                            "yes_man_eligible",
                            True,
                        )
                    ),

                "yes_man_qualified":
                    bool(
                        participant.get(
                            "yes_man_qualified",
                            False,
                        )
                    ),

                "troublemaker_qualified":
                    bool(
                        participant.get(
                            "troublemaker_qualified",
                            False,
                        )
                    ),

                "target_absurdity":
                    float(
                        participant.get(
                            "target_absurdity",
                            5,
                        )
                    ),
            },

            "events":
                result.get(
                    "Items",
                    [],
                ),
        },
    )


def require_finisher(pid):

    participant = (
        require_participant(
            pid
        )
    )

    if not (
        participant.get(
            "yes_man_qualified",
            False,
        )
        or
        participant.get(
            "troublemaker_qualified",
            False,
        )
    ):
        raise PermissionError(
            "participant has not completed the maze"
        )

    return participant


def finisher_classification(
    participant,
):

    if participant.get(
        "yes_man_qualified",
        False,
    ):
        return "yes-man"

    if participant.get(
        "troublemaker_qualified",
        False,
    ):
        return "troublemaker"

    return "unfinished"


def results_ledger(pid):

    requesting_participant = (
        require_finisher(
            pid
        )
    )

    items = scan_all()

    participants = {
        item.get(
            "participant_id"
        ):
            item
        for item
        in items
        if item.get(
            "record_type"
        ) == "participant"
    }

    events = []

    for item in items:

        if item.get(
            "record_type"
        ) not in {
            "response",
            "followup",
        }:
            continue

        participant = participants.get(
            item.get(
                "participant_id"
            ),
            {},
        )

        events.append(
            {
                "participant_id":
                    item.get(
                        "participant_id",
                        "",
                    ),

                "declared_name":
                    participant.get(
                        "declared_name",
                        "",
                    ),

                "record_type":
                    item.get(
                        "record_type",
                        "",
                    ),

                "question_id":
                    item.get(
                        "question_id",
                        "",
                    ),

                "presented_text":
                    item.get(
                        "presented_text",
                        "",
                    ),

                "response":
                    item.get(
                        "response",
                        "",
                    ),

                "classification":
                    item.get(
                        "classification",
                        "",
                    ),

                "followup_type":
                    item.get(
                        "followup_type",
                        "",
                    ),

                "created_at":
                    item.get(
                        "created_at",
                        "",
                    ),
            }
        )

    events.sort(
        key=lambda item:
            item.get(
                "created_at",
                "",
            ),
        reverse=True,
    )

    leaderboard = []

    for participant in (
        participants.values()
    ):

        leaderboard.append(
            {
                "participant_id":
                    participant.get(
                        "participant_id",
                        "",
                    ),

                "declared_name":
                    participant.get(
                        "declared_name",
                        "",
                    ),

                "question_count":
                    int(
                        participant.get(
                            "question_count",
                            0,
                        )
                    ),

                "affirmative_count":
                    int(
                        participant.get(
                            "affirmative_count",
                            0,
                        )
                    ),

                "refusal_count":
                    int(
                        participant.get(
                            "refusal_count",
                            0,
                        )
                    ),

                "classification":
                    finisher_classification(
                        participant
                    ),
            }
        )

    leaderboard.sort(
        key=lambda item:
            (
                item[
                    "question_count"
                ],
                item[
                    "affirmative_count"
                ],
                -item[
                    "refusal_count"
                ],
            ),
        reverse=True,
    )

    return reply(
        200,
        {
            "classification":
                finisher_classification(
                    requesting_participant
                ),

            "leaderboard":
                leaderboard,

            "events":
                events,

            "questions":
                [
                    serialize_question(
                        question
                    )
                    for question
                    in all_questions()
                ],
        },
    )


def create_question(
    pid,
    data,
):

    creator = (
        require_finisher(
            pid
        )
    )

    text = str(
        data.get(
            "text",
            "",
        )
    ).strip()

    interaction = str(
        data.get(
            "interaction",
            "",
        )
    ).strip()

    if not text:

        return reply(
            400,
            {
                "error":
                    "text is required"
            },
        )

    if interaction not in (
        VALID_INTERACTIONS
    ):

        return reply(
            400,
            {
                "error":
                    "invalid interaction"
            },
        )

    try:

        absurdity = Decimal(
            str(
                data.get(
                    "authored_absurdity",
                    0,
                )
            )
        )

    except Exception:

        return reply(
            400,
            {
                "error":
                    "authored_absurdity must be numeric"
            },
        )

    absurdity = max(
        Decimal("0"),
        min(
            Decimal("100"),
            absurdity,
        ),
    )

    choices = (
        data.get(
            "choices",
            [],
        )
        or []
    )

    if not isinstance(
        choices,
        list,
    ):

        return reply(
            400,
            {
                "error":
                    "choices must be a list"
            },
        )

    choices = [
        str(choice).strip()
        for choice
        in choices
        if str(choice).strip()
    ]

    if (
        interaction
        == "multiple_choice"
        and len(choices) < 2
    ):

        return reply(
            400,
            {
                "error":
                    "multiple_choice requires at least two choices"
            },
        )

    qid = str(
        uuid.uuid4()
    )

    item = {
        "pk":
            question_pk(qid),

        "sk":
            "META",

        "record_type":
            "question",

        "question_id":
            qid,

        "text":
            text[:5000],

        "interaction":
            interaction,

        "choices":
            choices[:20],

        "authored_absurdity":
            absurdity,

        "observed_absurdity":
            absurdity,

        "yes_count":
            0,

        "no_count":
            0,

        "active":
            True,

        "created_by":
            creator.get(
                "declared_name",
                pid,
            ),

        "created_by_participant_id":
            pid,

        "created_at":
            ts(),
    }

    table.put_item(
        Item=item
    )

    return reply(
        201,
        {
            "question":
                serialize_question(
                    item
                )
        },
    )


def lambda_handler(
    event,
    context,
):

    try:

        http = (
            event.get(
                "requestContext",
                {},
            )
            .get(
                "http",
                {},
            )
        )

        method = (
            http.get(
                "method",
                "",
            )
            .upper()
        )

        path = (
            event.get(
                "rawPath",
                "/",
            )
            .rstrip("/")
            or "/"
        )

        query = (
            event.get(
                "queryStringParameters"
            )
            or {}
        )

        session_id = (
            query.get(
                "session_id",
                "",
            )
        )

        participant_query = (
            query.get(
                "participant_id",
                "",
            )
        )

        if method == "OPTIONS":

            return reply(
                204,
                {},
            )

        if (
            method == "GET"
            and path == "/health"
        ):

            migrate_existing_seed_questions()

            return reply(
                200,
                {
                    "service":
                        "lovely-system-disclaimer",

                    "status":
                        "ok",

                    "engine":
                        "absurdity-v4",

                    "cooldown_days":
                        QUESTION_COOLDOWN_DAYS,
                },
            )

        if (
            method == "POST"
            and path == "/participants"
        ):

            return create_participant(
                parse_body(
                    event
                )
            )

        if (
            method == "GET"
            and path == "/results"
        ):

            return results_ledger(
                participant_query
            )

        if (
            method == "GET"
            and path == "/questions"
        ):

            return reply(
                200,
                {
                    "questions":
                        [
                            serialize_question(
                                question
                            )
                            for question
                            in all_questions()
                        ]
                },
            )

        if (
            method == "POST"
            and path == "/questions"
        ):

            data = parse_body(
                event
            )

            return create_question(
                str(
                    data.get(
                        "participant_id",
                        "",
                    )
                ),
                data,
            )

        parts = [
            part
            for part
            in path.split("/")
            if part
        ]

        if (
            len(parts) >= 2
            and parts[0]
                == "participants"
        ):

            pid = parts[1]

            if (
                method == "GET"
                and len(parts) == 2
            ):

                return participant_record(
                    pid
                )

            if (
                len(parts) == 3
                and not session_id
            ):

                return reply(
                    400,
                    {
                        "error":
                            "session_id is required"
                    },
                )

            if (
                method == "GET"
                and len(parts) == 3
                and parts[2] == "next"
            ):

                return next_question(
                    pid,
                    session_id,
                )

            if (
                method == "POST"
                and len(parts) == 3
                and parts[2] == "answer"
            ):

                return answer_question(
                    pid,
                    session_id,
                    parse_body(
                        event
                    ),
                )

            if (
                method == "POST"
                and len(parts) == 3
                and parts[2] == "followup"
            ):

                return record_followup(
                    pid,
                    session_id,
                    parse_body(
                        event
                    ),
                )

        return reply(
            404,
            {
                "error":
                    "not found"
            },
        )

    except PermissionError as error:

        return reply(
            403,
            {
                "error":
                    str(error)
            },
        )

    except LookupError as error:

        return reply(
            404,
            {
                "error":
                    str(error)
            },
        )

    except ValueError as error:

        return reply(
            400,
            {
                "error":
                    str(error)
            },
        )

    except Exception as error:

        print(
            "Unhandled failure:",
            repr(error),
        )

        return reply(
            500,
            {
                "error":
                    "internal server error"
            },
        )
