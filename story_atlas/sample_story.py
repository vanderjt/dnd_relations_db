"""Greyhaven tutorial data; published only to a brand-new database filename."""
from datetime import datetime, timezone
from uuid import uuid4
from .backup import publish_database
from .database import Database
from .paths import validate_writable_location
from .greyhaven import EXTRA_CAST, EVENTS, CONNECTIONS

CAST = (
    dict(name="Mira Vale", role="Apothecary", species="Human", faction="Lantern Guild", location="Greyhaven Market", status="Active",
         summary="A practical healer investigating a sickness spreading through the docks.",
         backstory="Returned to Greyhaven after training abroad; her missing brother left a ledger of suspicious shipments.",
         traits="Patient, skeptical, fiercely loyal", skills="Herbalism, medicine, investigation", inventory="Healer's kit, brass lantern, brother's ledger",
         notes="Wants proof before accusing the city council.", tags="Protagonist, Healer"),
    dict(name="Thorne Blackwood", role="Harbor watch captain", species="Half-elf", faction="Harbor Watch", location="North Gate", status="Active",
         summary="A veteran captain caught between duty and an old debt.", backstory="Mira saved his patrol during a winter siege.",
         traits="Disciplined, guarded", skills="Swordplay, tactics", inventory="Watch badge, longsword", notes="Secretly protects a smuggling witness.", tags="Watch, Ally"),
    dict(name="Pip Copperwhistle", role="Courier and tinkerer", species="Gnome", faction="Lantern Guild", location="Old Quay", status="Active",
         summary="A fast-talking messenger who knows every rooftop route.", backstory="Grew up repairing dock machinery and carrying messages for sailors.",
         traits="Curious, optimistic, impulsive", skills="Lockpicking, gadgets, rooftop running", inventory="Tool roll, grappling hook, clockwork bird",
         notes="Mira teaches Pip first aid; Pip brings her rumors.", tags="Courier, Witness"),
    dict(name="Seraphine Ash", role="Merchant patron", species="Tiefling", faction="Ash Trading Company", location="Merchant Quarter", status="Active",
         summary="A charming benefactor whose generosity buys silence.", backstory="Built a trade empire after her family's exile.",
         traits="Elegant, calculating", skills="Negotiation, illusion", inventory="Signet ring, shipping contracts", notes="An alliance becomes a rivalry after the ledger is revealed.", tags="Antagonist, Merchant"),
    dict(name="Elias Reed", role="Retired archivist", species="Human", faction="City Archive", location="Riverside Cottage", status="Missing",
         summary="A quiet historian who recognized the seal on a forbidden shipment.", backstory="Catalogued the city's records for forty years.",
         traits="Meticulous, anxious", skills="History, languages, ciphers", inventory="Cipher notebook, archive key", notes="Last seen following a lantern toward the docks.", tags="Mystery, Scholar"),
)


def create_sample(destination):
    destination = validate_writable_location(destination)
    def populate(path):
        db = Database(path)
        try:
            motivations = ('Find Rowan and stop the dockside sickness.', 'Protect witnesses without destroying the Watch.',
                           'Prove useful without putting friends at risk.', 'Keep the company solvent while protecting Corin.',
                           'Preserve the evidence and reach a public hearing alive.')
            original_cast = [dict(row, goals=motivation) for row, motivation in zip(CAST, motivations)]
            types = dict(mira='Player', pip='Player', seraphine='Merchant', corin='Merchant',
                         ada='Merchant', oren='Merchant', garrick='Enemy NPC', dorian='Neutral NPC',
                         elias='Neutral NPC')
            ids = {}
            for row in (*original_cast, *EXTRA_CAST):
                key = row['name'].split()[0].lower()
                goals = row.get('goals') or row['notes'].removeprefix('Motivation: ')
                ids[key] = db.save_character(dict(row, goals=goals, character_type=types.get(key, 'Allied NPC')))
            mira, thorne, pip, seraphine, elias = [ids[key] for key in ('mira', 'thorne', 'pip', 'seraphine', 'elias')]
            events = {sequence: db.events.save(title, summary, sequence,
                                              [ids[key] for key in cast.split()])
                      for sequence, title, summary, cast in EVENTS}
            # Several scenes per chapter; the ten existing event IDs/order keep
            # all sample relationship beginnings and changes at the same points.
            for title, summary, orders in (
                    ('Lanterns in the fog', 'The cast follows the first clues through the docks.', range(1, 4)),
                    ('The cost of silence', 'Secrets split alliances as the city closes in.', range(4, 8)),
                    ('A city answers', 'A rescue and public reckoning determine Greyhaven’s future.', range(8, 11))):
                chapter = db.chapters.save(title, summary)
                with db.connection:
                    db.connection.executemany('UPDATE story_events SET chapter_id=? WHERE id=?',
                                             [(chapter, events[order]) for order in orders])
            db.save_relationship(mira, thorne, "Friend", "They trust each other after the siege.", semantics="mutual")
            db.save_relationship(mira, pip, "Mentor", "First-aid lessons in exchange for dockside news.", inverse_label="Mentee")
            db.save_relationship(seraphine, pip, "Employer", "Pip delivers sealed contracts without reading them.", inverse_label="Employee")
            db.save_relationship(thorne, seraphine, "Rival", "Thorne suspects her ships; her response is unknown.")
            db.save_relationship(elias, mira, "Ally", "Elias decoded the ledger's shipping marks.")
            db.save_relationship(pip, elias, "Friend", "Weekly deliveries to the cottage.", semantics="mutual")
            link = db.save_relationship(mira, seraphine, "Ally", "An uneasy agreement.", semantics="mutual", start_event=events[2])
            state = next(row for row in db.relationships() if row["id"] == link)
            db.history.write(link, events[5], dict(state, kind="Enemy", semantics="directional", notes="Mira confronts Seraphine. Her hostility is one-sided unless explicitly changed."))
            links = {}
            for source, target, kind, notes, shared, inverse, chapter in CONNECTIONS:
                links[(source, target, kind)] = db.save_relationship(ids[source], ids[target], kind, notes,
                    semantics='mutual' if shared else 'directional', inverse_label=inverse,
                    start_event=events[chapter] if chapter else None)
            # End and resume the same canonical connection, retaining its history.
            ident = links[('thorne', 'sable', 'Ally')]
            state = next(row for row in db.relationships(events[4]) if row['id'] == ident)
            db.history.write(ident, events[6], dict(state, notes='The blockade interrupts cooperation.'), active=False)
            db.history.write(ident, events[8], dict(state, notes='The storm rescue renews their alliance.'), active=True)
            ident = links[('dorian', 'garrick', 'Political ally')]
            state = next(row for row in db.relationships(events[8]) if row['id'] == ident)
            db.history.write(ident, events[9], dict(state, notes='The hearing ends the political alliance.'), active=False)
            # Profiles describe Current; the chronology records the earlier disappearance.
            row = next(row for row in db.characters() if row['id'] == elias)
            db.save_character(dict(row, status='Active', notes='Rescued in event 7; his testimony matters in event 9.', goals='Protect the archives and testify truthfully.'), elias)
            with db.connection:
                db.connection.execute("INSERT INTO story_metadata VALUES ('title', 'Greyhaven')")
            from .example_views import save_example_views
            categories = {kind: group for group, kinds in (
                ('Support', ('Ally', 'Mentor', 'Colleague', 'Research partner', 'Patron', 'Protector', 'Rescuer', 'Supplier', 'Navigator', 'Volunteer', 'Donor')),
                ('Conflict', ('Enemy', 'Rival', 'Blackmailer', 'Distrust', 'Captor')),
                ('Personal', ('Friend', 'Family')),
                ('Other', ('Employer', 'Commander', 'Creditor', 'Business partner', 'Coworker', 'Political ally', 'Investigator', 'Reporter', 'Witness', 'Courier', 'Negotiator')),
            ) for kind in kinds}
            save_example_views(db, categories, (
                ('01 · A fragile pact', events[2], mira),
                ('02 · The ledger changes the alliance', events[5], mira),
                ('03 · Cooperation interrupted', events[6], thorne),
                ('04 · Cooperation renewed', events[8], thorne)))
        finally:
            db.close()
    return publish_database(destination, populate)


def new_sample(root, example='greyhaven'):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    if example == 'prometheus':
        from .prometheus import create_prometheus
        return create_prometheus(root / 'stories' / f'the-modern-prometheus-{stamp}-{uuid4().hex[:8]}.db')
    if example != 'greyhaven':
        raise ValueError('Choose Greyhaven or the modern prometheus.')
    return create_sample(root / "stories" / f"Greyhaven-{stamp}-{uuid4().hex[:8]}.db")
