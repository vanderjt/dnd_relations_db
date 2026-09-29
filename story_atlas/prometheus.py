"""A chronological, explicitly interpreted model of Shelley's 1831 Frankenstein.

Public-domain source: https://www.gutenberg.org/files/42324/42324-h/42324-h.htm
Summaries are original paraphrases. Player/NPC labels are modeling choices.
"""
from .backup import publish_database
from .database import Database
from .paths import validate_writable_location
from .example_views import save_example_views

SOURCE = 'https://www.gutenberg.org/files/42324/42324-h/42324-h.htm'

# Key, name, current type, introduction, occupation, current status, summary, goals.
CAST = (
    ('victor', 'Victor Frankenstein', 'Player', 1, 'Natural philosopher and creator', 'Dead',
     'His pursuit of knowledge becomes a refusal of responsibility, followed by revenge.',
     'Early: discover the principle of life. Later: contain the consequences. Final: destroy the creature.'),
    ('creature', 'The creature', 'Enemy NPC', 4, 'Created being and embedded narrator', 'Last seen departing into the Arctic; death unconfirmed',
     'An articulate, lonely being seeks belonging, commits murders, and finally expresses remorse. Enemy NPC describes opposition to Victor, not a verdict on his worth.',
     'First: find shelter, language and acceptance. Then: secure a companion. Later: punish Victor. Final: announce his own destruction.'),
    ('elizabeth', 'Elizabeth Lavenza', 'Allied NPC', 1, 'Victor’s adopted companion and eventual wife', 'Dead',
     'A cherished member of the Frankenstein household who supports Justine and hopes for a life with Victor.',
     'Protect her family, defend Justine, and understand Victor’s secrecy.'),
    ('henry', 'Henry Clerval', 'Allied NPC', 1, 'Friend, traveler and student of languages', 'Dead',
     'Victor’s childhood friend nurses him through illness and later travels with him in Britain.',
     'Help Victor recover while pursuing his own studies and travels.'),
    ('alphonse', 'Alphonse Frankenstein', 'Allied NPC', 1, 'Father and Genevan citizen', 'Dead',
     'Supports Victor through loss, but cannot understand the secret driving his son’s distress.',
     'Keep the family together and restore Victor’s peace.'),
    ('caroline', 'Caroline Beaufort Frankenstein', 'Allied NPC', 1, 'Mother', 'Dead',
     'Brings Elizabeth into the family; dies after nursing her through scarlet fever.',
     'Care for her children and see Victor and Elizabeth united.'),
    ('william', 'William Frankenstein', 'Neutral NPC', 1, 'Victor’s youngest brother', 'Dead',
     'His murder becomes the first direct attack on Victor’s family.',
     'Enjoy the security and affection of his family.'),
    ('ernest', 'Ernest Frankenstein', 'Neutral NPC', 1, 'Victor’s brother', 'Alive at last mention',
     'A surviving family member whose life is overshadowed by successive losses.',
     'Remain connected to his family as the household breaks apart.'),
    ('justine', 'Justine Moritz', 'Allied NPC', 1, 'Household attendant and family companion', 'Executed',
     'Wrongly convicted of William’s murder after the creature plants incriminating evidence.',
     'Maintain her innocence and retain Elizabeth’s trust despite coercion.'),
    ('waldman', 'M. Waldman', 'Neutral NPC', 3, 'Professor at Ingolstadt', 'Alive at last mention',
     'Encourages Victor’s study of modern natural philosophy without knowing the later experiment.',
     'Guide Victor toward disciplined scientific study.'),
    ('delacey', 'De Lacey', 'Neutral NPC', 6, 'Blind father of an exiled family', 'Alive at last mention',
     'Offers the unseen creature a sympathetic hearing before the encounter is interrupted.',
     'Support his family through poverty and exile.'),
    ('felix', 'Felix De Lacey', 'Neutral NPC', 6, 'Exile and Safie’s beloved', 'Alive at last mention',
     'Helps Safie’s father escape imprisonment, suffers exile, and later violently rejects the creature.',
     'Protect his family and build a life with Safie.'),
    ('agatha', 'Agatha De Lacey', 'Neutral NPC', 6, 'Daughter in the cottage household', 'Alive at last mention',
     'Her acts of care help the observing creature understand affection and family life.',
     'Care for her father and sustain the household.'),
    ('safie', 'Safie', 'Neutral NPC', 6, 'Traveler and language learner', 'Alive at last mention',
     'Rejects her father’s command and joins Felix; her lessons also educate the hidden creature.',
     'Choose her own future, reunite with Felix, and learn the household’s language.'),
    ('merchant', 'Safie’s father', 'Merchant', 6, 'Turkish merchant', 'Alive at last mention',
     'Escapes imprisonment with Felix’s help, then repudiates the promised marriage and orders Safie to leave.',
     'Preserve his safety and control his daughter’s marriage. This is a character’s conduct, not a claim about his culture.'),
    ('walton', 'Robert Walton', 'Player', 18, 'Arctic expedition captain and frame narrator', 'Alive; returning south',
     'Recognizes his own ambition in Victor, but ultimately agrees to turn back for his crew.',
     'Seek discovery and friendship; finally choose his crew’s survival over glory.'),
    ('margaret', 'Margaret Saville', 'Neutral NPC', 18, 'Walton’s sister and letter recipient', 'Alive',
     'Receives the letters that frame Victor’s account and the creature’s final appearance.',
     'Her inner goals are not supplied by the novel; she is represented as the receiving audience.'),
)

# Order, title, summary, participants; these are selected scenes, not book chapter numbers.
EVENTS = (
    (1, 'A family in Geneva', 'Elizabeth joins the Frankenstein household; Victor grows up with family affection and Henry’s friendship. This example follows selected events in chronological order, not the novel’s nested narration. Source: Mary Shelley, 1831 edition, chapters 1–2. Player/NPC types are current modeling labels; profile status and goals are not historical fields.', 'victor elizabeth henry alphonse caroline william ernest justine'),
    (2, 'Caroline’s final wish', 'Caroline nurses Elizabeth through scarlet fever, contracts the illness, and dies. She hopes Victor and Elizabeth will marry. Victor’s departure for Ingolstadt is delayed by grief. Chapter 3.', 'caroline elizabeth victor alphonse'),
    (3, 'Waldman opens a door', 'At Ingolstadt, Waldman encourages Victor to study modern science. Victor becomes absorbed in the origins of life. Chapters 3–4.', 'victor waldman'),
    (4, 'Life, followed by abandonment', 'Victor animates the being he has assembled and recoils from him. The creature enters the visible cast here. The lasting Creator connection is separate from the changing relationship of responsibility and hostility. Chapter 5.', 'victor creature'),
    (5, 'Clerval’s care', 'Henry arrives and nurses Victor through a prolonged illness. Victor conceals the experiment. Chapters 5–6.', 'victor henry'),
    (6, 'Learning beside the cottage', 'The hidden creature observes De Lacey, Felix and Agatha, secretly gathers fuel, and learns through Safie’s lessons. Their earlier exile and the merchant’s betrayal are recounted here as backstory, not newly occurring actions. Chapters 11–14.', 'creature delacey felix agatha safie merchant'),
    (7, 'The appeal and the rejection', 'The creature speaks to blind De Lacey, who hears him sympathetically. Felix returns and strikes him; Safie and Agatha react in fear. The family leaves. The creature later burns the empty cottage. Chapters 15–16.', 'creature delacey felix agatha safie'),
    (8, 'William murdered; Justine framed', 'Near Geneva, the creature kills William after learning his family name, then plants the miniature on the sleeping Justine. Victor later suspects the creature. The events are confessed retrospectively in chapter 16; their consequences appear in chapter 7.', 'creature william justine victor'),
    (9, 'Justine’s conviction', 'Elizabeth testifies to Justine’s character. A coerced confession and circumstantial evidence lead to Justine’s execution. Victor’s silence leaves him consumed by guilt. Chapter 8.', 'justine elizabeth victor alphonse'),
    (10, 'The glacier bargain', 'On the glacier, the creature tells his story and asks for a companion. Victor agrees on condition that the pair leave human society. Load the saved view for this scene to see a temporary agreement replace abandonment on the same connection. Chapters 10 and 17.', 'victor creature'),
    (11, 'A journey with a secret purpose', 'Victor travels with Henry through Britain, then separates from him to work alone in the Orkneys. Henry does not know what Victor is making. Chapters 18–19.', 'victor henry'),
    (12, 'The companion destroyed', 'Victor destroys the unfinished companion before animating her. The watching creature confronts him and threatens his wedding night. No living second creature is added: this is an uncompleted creation, recorded in the event. Chapter 20.', 'victor creature'),
    (13, 'Henry’s death in Ireland', 'Henry is murdered by the creature. Victor is accused, collapses, and is later cleared. Alphonse comes to support him. Chapters 21–22.', 'henry creature victor alphonse'),
    (14, 'Victor and Elizabeth marry', 'Victor marries Elizabeth while misreading the threat as directed chiefly against himself. The Intended marriage connection becomes Spouse at this event. Chapter 22.', 'victor elizabeth alphonse'),
    (15, 'The wedding-night murder', 'The creature kills Elizabeth while Victor searches for an attacker elsewhere. Victor sees the creature outside. The active spousal relationship ends here; its earlier states remain in History. Chapter 23.', 'victor elizabeth creature'),
    (16, 'Alphonse dies of grief', 'The death of Elizabeth overwhelms Alphonse, who dies soon afterward. Victor’s surviving purpose turns toward revenge. Chapter 23.', 'alphonse victor'),
    (17, 'The pursuit north', 'Victor vows vengeance and pursues the creature across vast distances. The creature leaves signs and provisions that prolong the chase. Their changing connection becomes mutual pursuit; the Creator connection remains a separate historical fact. Chapter 24.', 'victor creature'),
    (18, 'Walton rescues Victor', 'Walton’s crew takes the exhausted Victor aboard. Victor recounts the history that makes up most of the novel. Margaret appears as the recipient of Walton’s letters, not as a passenger physically present on the ship. Letter 4 and chapter 24.', 'walton victor margaret'),
    (19, 'A retreat and a death', 'Walton agrees to return south when the ice permits, despite Victor’s appeal to ambition. Victor dies aboard the ship. The pursuit ends; Walton’s choice interrupts the repetition of Victor’s obsession. Walton’s continuation, chapter 24.', 'walton victor'),
    (20, 'The creature’s farewell', 'The creature mourns over Victor’s body, speaks with Walton about guilt and suffering, and announces that he will destroy himself. He departs on an ice raft. The novel does not show his death. Walton’s continuation, chapter 24. Source: ' + SOURCE, 'creature walton'),
)

CHAPTERS = (
    ('01 · Family and ambition', 'A household, a loss, and the beginnings of Victor’s ambition.', range(1, 4)),
    ('02 · Creation and care', 'Creation without care is contrasted with Henry’s practical friendship.', range(4, 6)),
    ('03 · Education and rejection', 'The creature’s account explains learning, failed belonging, and violence. Cottage backstory is explicitly marked.', range(6, 10)),
    ('04 · A promise broken', 'A conditional agreement collapses into renewed violence.', range(10, 14)),
    ('05 · Marriage, loss, pursuit', 'Personal bonds are destroyed and revenge becomes Victor’s purpose.', range(14, 18)),
    ('06 · The Arctic frame', 'Walton receives the story and chooses retreat. The creature’s death remains unconfirmed.', range(18, 21)),
)


def create_prometheus(destination):
    def populate(path):
        db = Database(path)
        try:
            ids, intros = {}, {}
            for key, name, kind, intro, role, status, summary, goals in CAST:
                ids[key] = db.save_character(dict(name=name, character_type=kind, role=role,
                    species='Created being' if key == 'creature' else 'Human', status=status,
                    summary=summary, goals=goals, tags='Frankenstein, 1831 edition',
                    notes='Source: ' + SOURCE + '\nSelected-scene model. Current type/status and stage-labeled goals are not time-versioned.'))
                intros[key] = intro
            events = {order: db.events.save(title, summary, order, [ids[k] for k in cast.split()])
                      for order, title, summary, cast in EVENTS}
            for title, summary, orders in CHAPTERS:
                chapter = db.chapters.save(title, summary)
                with db.connection:
                    db.connection.executemany('UPDATE story_events SET chapter_id=? WHERE id=?',
                                             [(chapter, events[n]) for n in orders])
            for key, ident in ids.items():
                row = next(r for r in db.characters() if r['id'] == ident)
                db.save_character(dict(row, introduction_event_id=events[intros[key]]), ident)

            links = {}
            def link(key, source, target, kind, event, notes, mutual=False, inverse=''):
                links[key] = db.save_relationship(ids[source], ids[target], kind, notes,
                    semantics='mutual' if mutual else 'directional', inverse_label=inverse,
                    start_event=events[event])
                return links[key]

            def change(key, event, kind=None, notes='', active=True, mutual=None):
                ident = links[key]
                state = db.history.editing_state(ident, events[event])
                if kind:
                    state['kind'] = kind
                if mutual is not None:
                    state['semantics'] = 'mutual' if mutual else 'directional'
                    state['inverse_label'] = ''
                state['notes'] = notes
                db.history.write(ident, events[event], state, active=active)

            for child in ('victor', 'william', 'ernest'):
                link('father-' + child, 'alphonse', child, 'Father', 1, 'Family relation; retained as a historical fact after death.', inverse='Son')
                link('mother-' + child, 'caroline', child, 'Mother', 1, 'Family relation; death does not erase parentage.', inverse='Son')
            link('adoption', 'caroline', 'elizabeth', 'Adoptive mother', 1, '1831 version: Elizabeth is adopted into the household, not Victor’s biological cousin.', inverse='Adopted daughter')
            link('parents', 'alphonse', 'caroline', 'Spouse', 1, 'A marriage founded on care.', True)
            change('parents', 2, notes='Caroline dies; the active marriage ends.', active=False)
            link('henry', 'victor', 'henry', 'Friend', 1, 'A mutual childhood friendship.', True)
            change('henry', 5, notes='Henry nurses Victor without knowing his secret.')
            change('henry', 13, notes='Henry is murdered; friendship survives in Victor’s memory, not as an active interaction.', active=False)
            link('marriage', 'victor', 'elizabeth', 'Intended marriage', 2, 'Caroline’s hope and their attachment point toward marriage.', True)
            change('marriage', 14, 'Spouse', 'Victor and Elizabeth marry.', mutual=True)
            change('marriage', 15, notes='Elizabeth is murdered on the wedding night.', active=False)
            link('justine', 'elizabeth', 'justine', 'Friend', 1, 'Elizabeth trusts and values Justine.', True)
            change('justine', 9, notes='Justine is executed despite Elizabeth’s testimony.', active=False)
            link('defence', 'elizabeth', 'justine', 'Defender', 9, 'Elizabeth publicly defends Justine’s character.', inverse='Defended person')
            link('teacher', 'waldman', 'victor', 'Teacher', 3, 'Waldman encourages study, not the secret act of creation.', inverse='Student')
            link('creator', 'victor', 'creature', 'Creator', 4, 'A lasting fact of origin, separate from their changing personal relationship.', inverse='Creation')
            link('bond', 'victor', 'creature', 'Abandonment', 4, 'Victor rejects the dependent being he has animated.')
            change('bond', 10, 'Conditional agreement', 'Victor promises a companion; the creature promises to withdraw from human society.', mutual=True)
            change('bond', 12, 'Broken promise', 'Victor destroys the unfinished companion and repudiates the agreement.', mutual=False)
            change('bond', 17, 'Pursuit', 'Victor pursues the creature; the creature sustains the chase with messages and provisions.', mutual=True)
            change('bond', 19, notes='Victor dies, ending the pursuit.', active=False)
            for child in ('felix', 'agatha'):
                link('delacey-' + child, 'delacey', child, 'Father', 6, 'Family tie within the exiled household.', inverse='Child')
            link('safie-father', 'merchant', 'safie', 'Father', 6, 'Her father tries to control her destination and marriage.', inverse='Daughter')
            link('safie-felix', 'felix', 'safie', 'Lovers', 6, 'Safie joins Felix after defying her father.', True)
            link('safie-lessons', 'felix', 'safie', 'Teacher', 6, 'Her language lessons also educate the hidden creature.', inverse='Student')
            link('merchant-felix', 'merchant', 'felix', 'Betrayal', 6, 'Backstory revealed at the cottage: after Felix helps his escape, the merchant repudiates the marriage promise.')
            link('helper', 'creature', 'delacey', 'Secret helper', 6, 'The creature brings fuel anonymously; this is not a mutually acknowledged friendship.')
            change('helper', 7, notes='The household departs and the secret assistance ends.', active=False)
            link('hearing', 'delacey', 'creature', 'Sympathetic listener', 7, 'De Lacey hears the stranger kindly; no lasting friendship is established.')
            link('rejection', 'felix', 'creature', 'Violent rejection', 7, 'Felix strikes the creature on finding him beside his father.')
            link('william-murder', 'creature', 'william', 'Killed', 8, 'The creature confesses this killing in his later account. This link records an act, not an ongoing living interaction.', inverse='Killed by')
            link('framing', 'creature', 'justine', 'Framed', 8, 'The miniature is planted on the sleeping Justine.', inverse='Framed by')
            link('henry-murder', 'creature', 'henry', 'Killed', 13, 'Henry’s murder punishes Victor through someone he loves.', inverse='Killed by')
            link('elizabeth-murder', 'creature', 'elizabeth', 'Killed', 15, 'The wedding-night threat is carried out against Elizabeth.', inverse='Killed by')
            link('walton-family', 'walton', 'margaret', 'Sibling', 18, 'The relationship predates the action; it enters this model with the Arctic frame.', True)
            link('letters', 'walton', 'margaret', 'Correspondent', 18, 'Walton’s letters carry the framed account; Margaret is not aboard the ship.', inverse='Recipient')
            link('rescue', 'walton', 'victor', 'Rescuer', 18, 'Walton’s ship receives the exhausted traveler.', inverse='Rescued person')
            link('walton-victor', 'walton', 'victor', 'Friend', 18, 'Walton finds a friend and an unsettling mirror of his ambition.', True)
            change('walton-victor', 19, notes='Victor dies after Walton chooses retreat.', active=False)
            link('testimony', 'creature', 'walton', 'Final testimony', 20, 'The creature describes remorse and intended self-destruction. Walton witnesses his departure, not his death.', inverse='Listener')
            with db.connection:
                db.connection.execute("INSERT INTO story_metadata VALUES ('title', 'the modern prometheus')")
            categories = {kind: group for group, kinds in (
                ('Support', ('Teacher', 'Defender', 'Secret helper', 'Sympathetic listener', 'Rescuer', 'Conditional agreement')),
                ('Conflict', ('Abandonment', 'Broken promise', 'Pursuit', 'Betrayal', 'Violent rejection', 'Killed', 'Framed')),
                ('Personal', ('Father', 'Mother', 'Adoptive mother', 'Spouse', 'Friend', 'Intended marriage', 'Lovers', 'Sibling')),
                ('Other', ('Creator', 'Correspondent', 'Final testimony')),
            ) for kind in kinds}
            save_example_views(db, categories, (
                ('01 · Creation and abandonment', events[4], ids['victor']),
                ('02 · The creature seeks belonging', events[7], ids['creature']),
                ('03 · The glacier bargain', events[10], ids['creature']),
                ('04 · The promise breaks', events[12], ids['creature']),
                ('05 · Marriage before the murder', events[14], ids['elizabeth']),
                ('06 · The Arctic ending', events[20], ids['walton'])))
            db.history.validate()
        finally:
            db.close()
    return publish_database(validate_writable_location(destination), populate)
