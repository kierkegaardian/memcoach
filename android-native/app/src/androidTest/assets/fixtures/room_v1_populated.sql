INSERT INTO kids (id, name, createdAtEpochMillis)
VALUES (1, 'Fixture Kid', 1752537600000);

INSERT INTO kids (id, name, createdAtEpochMillis)
VALUES (2, 'Second Fixture Kid', 1752537601000);

INSERT INTO decks (id, name, createdAtEpochMillis)
VALUES (1, 'Fixture Deck', 1752537600000);

INSERT INTO decks (id, name, createdAtEpochMillis)
VALUES (2, 'Second Fixture Deck', 1752537601000);

INSERT INTO cards (
    id, deckId, prompt, fullText, intervalDays, easeFactor, streak,
    dueDateEpochDay, createdAtEpochMillis
) VALUES (
    1, 1, 'Fixture prompt', 'Fixture answer', 1, 2.5, 0,
    20284, 1752537600000
);

INSERT INTO cards (
    id, deckId, prompt, fullText, intervalDays, easeFactor, streak,
    dueDateEpochDay, createdAtEpochMillis
) VALUES (
    2, 1, 'Second prompt', 'Second answer', 3, 2.35, 2,
    20287, 1752537601000
);

INSERT INTO cards (
    id, deckId, prompt, fullText, intervalDays, easeFactor, streak,
    dueDateEpochDay, createdAtEpochMillis
) VALUES (
    3, 2, 'Third prompt', 'Third answer', 10, 2.7, 4,
    20294, 1752537602000
);

INSERT INTO card_progress (
    kidId, cardId, intervalDays, easeFactor, streak, dueDateEpochDay,
    lastReviewEpochMillis
) VALUES (
    1, 1, 6, 2.5, 1, 20290, 1752541323000
);

INSERT INTO card_progress (
    kidId, cardId, intervalDays, easeFactor, streak, dueDateEpochDay,
    lastReviewEpochMillis
) VALUES (
    1, 2, 3, 2.35, 2, 20287, 1752544923000
);

INSERT INTO card_progress (
    kidId, cardId, intervalDays, easeFactor, streak, dueDateEpochDay,
    lastReviewEpochMillis
) VALUES (
    2, 1, 1, 2.3, 0, 20285, 1752548523000
);

INSERT INTO card_progress (
    kidId, cardId, intervalDays, easeFactor, streak, dueDateEpochDay,
    lastReviewEpochMillis
) VALUES (
    2, 3, 10, 2.7, 4, 20294, 1752552123000
);

INSERT INTO reviews (
    id, cardId, kidId, grade, userText, durationSeconds, createdAtEpochMillis
) VALUES (
    1, 1, 1, 'perfect', 'Fixture answer', 12, 1752541323000
);

INSERT INTO reviews (
    id, cardId, kidId, grade, userText, durationSeconds, createdAtEpochMillis
) VALUES (
    2, 2, 1, 'good', 'Second answer.', 18, 1752544923000
);

INSERT INTO reviews (
    id, cardId, kidId, grade, userText, durationSeconds, createdAtEpochMillis
) VALUES (
    3, 1, 2, 'fail', '', NULL, 1752548523000
);

INSERT INTO reviews (
    id, cardId, kidId, grade, userText, durationSeconds, createdAtEpochMillis
) VALUES (
    4, 3, 2, 'perfect', 'Third answer', 9, 1752552123000
);

INSERT INTO reviews (
    id, cardId, kidId, grade, userText, durationSeconds, createdAtEpochMillis
) VALUES (
    5, 3, 2, 'good', 'Third answer', 11, 1752638523000
);
