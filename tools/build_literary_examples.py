"""Author ordinary saved preview stories through the app's validated save API.

Never overwrites existing stories. Pass an empty --output folder to regenerate.
The editorial scene groupings are not the novels' original chapter divisions.
"""
import argparse
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from story_atlas.preview_store import PreviewStore
from story_atlas.prometheus import CAST, EVENTS, CHAPTERS, SOURCE

DRACULA_SOURCE = 'https://www.gutenberg.org/cache/epub/45839/pg45839-images.html'


class Author:
    def __init__(self, path, title, source):
        self.store = PreviewStore.create(path, title)
        self.source = source
        self.cast = {}
        self.links = {}
        self.locations = {}

    def save(self, command, **payload):
        return self.store.write(command, payload, self.store.revision(), uuid.uuid4().hex)['data']

    def character(self, key, name, role, summary, goals, species='Human', **extra):
        ident = self.save('create_character', name=name, summary=summary, event_id=1)['character_id']
        self.cast[key] = ident
        self.profile(key, 1, role=role, species=species, goals=goals, status='Alive',
                     notes='Source: ' + self.source + '\nEditorial study with full spoilers. All cast members are visible in the roster; participation tags identify the people involved in each scene. Unknown ages are left blank.', **extra)

    def profile(self, key, event, **values):
        self.save('save_profile', character_id=self.cast[key], event_id=event,
                  changes=[dict(field=k, value=v, scope='carry_forward') for k, v in values.items()])

    def chapter(self, number, title, summary):
        args = dict(title=title, summary=summary)
        if number == 1:
            args['id'] = 1
        return self.save('save_chapter', **args)['id']

    def event(self, number, chapter, title, summary, purpose, location, participants, reference):
        if location not in self.locations:
            self.locations[location] = self.save('save_world', category='location', name=location,
                description='Setting used in this literary scene model. See the event notes for source references.')['id']
        args = dict(chapter_id=chapter, title=title, summary=summary, purpose=purpose,
                    status='Happened', location_id=self.locations[location],
                    participants=[self.cast[k] for k in participants.split()],
                    notes=reference + '\nSource: ' + self.source + '\nScene titles, grouping, purposes and relationship labels are editorial interpretations. Participation may include a person discussed or addressed, not only someone physically present.')
        if number == 1:
            args['id'] = 1
        ident = self.save('save_event', **args)['id']
        assert ident == number

    def link(self, event, source, target, kind, notes, category='Personal', inverse=''):
        pair = tuple(sorted((source, target)))
        args = dict(event_id=event, source_id=self.cast[source], target_id=self.cast[target],
                    kind=kind, notes=notes, category=category, inverse_label=inverse,
                    semantics='directional' if inverse else 'mutual', scope='carry_forward')
        if pair in self.links:
            args['id'] = self.links[pair]
        self.links[pair] = self.save('save_connection', **args)['id']

    def finish(self, event=1, character=None):
        self.store.save_preference('theme', 'gothic')
        self.store.save_preference('context', dict(page='story', event_id=event,
            character_id=self.cast[character or next(iter(self.cast))]))
        self.store.close()


def frankenstein(path):
    a = Author(path, 'Frankenstein — Mary Shelley (1831)', SOURCE)
    for key, name, kind, intro, role, status, summary, goals in CAST:
        summary = summary.replace(' Enemy NPC describes opposition to Victor, not a verdict on his worth.', '')
        a.character(key, name, role, summary, goals, 'Created being' if key == 'creature' else 'Human')
    chapters = {}
    for number, (title, summary, orders) in enumerate(CHAPTERS, 1):
        cid = a.chapter(number, title, summary)
        chapters.update({e: cid for e in orders})
    places = ['Geneva', 'Geneva', 'Ingolstadt', 'Ingolstadt', 'Ingolstadt',
              'De Lacey cottage', 'De Lacey cottage', 'Geneva', 'Geneva', 'Montanvert glacier',
              'Britain', 'Orkney Islands', 'Ireland', 'Geneva', 'Evian', 'Geneva',
              'Northern Europe and Russia', 'Arctic Ocean', 'Arctic Ocean', 'Arctic Ocean']
    purposes = ['Establish the family bonds that ambition will put at risk.',
        'Make loss a pressure behind Victor’s desire to overcome death.',
        'Turn curiosity into an isolating scientific ambition.',
        'Separate the ability to create life from the willingness to care for it.',
        'Contrast Henry’s practical care with Victor’s abandonment.',
        'Give the creature a language and an understanding of human affection.',
        'Break the hope that a sympathetic hearing will secure belonging.',
        'Turn rejection into deliberate harm and misdirected blame.',
        'Show how secrecy and coercion destroy an innocent person.',
        'Offer a conditional way out of the cycle of violence.',
        'Bring companionship and a concealed obligation into conflict.',
        'Destroy the bargain and redirect vengeance toward the wedding.',
        'Force Victor to confront the cost paid by his closest friend.',
        'Place a hoped-for future beside a misunderstood threat.',
        'Complete the destruction of Victor’s imagined domestic future.',
        'Leave revenge as Victor’s consuming purpose.',
        'Make creator and creation sustain the same destructive obsession.',
        'Return the chronological account to Walton’s framing narrative.',
        'Let Walton reject the ruinous ambition Victor still defends.',
        'End with remorse and an announced intention, not a witnessed death.']
    for number, title, summary, cast in EVENTS:
        summary = summary.replace(' Player/NPC types are current modeling labels; profile status and goals are not historical fields.', '')
        summary = summary.replace('The creature enters the visible cast here. The lasting Creator connection is separate from the changing relationship of responsibility and hostility.', 'The creature comes to life here. Their shared origin and changing hostility are recorded on one evolving connection.')
        summary = summary.split(' Load the saved view')[0] if number == 10 else summary
        summary = summary.replace('The Creator connection remains a separate historical fact.', 'Creation remains a historical fact.')
        summary = summary.replace('the Creator connection remains a separate historical fact.', 'creation remains a historical fact.')
        summary = summary.replace('The active spousal relationship ends here; its earlier states remain in History.', 'Their marriage is cut short; the connection records bereavement from this event.')
        a.event(number, chapters[number], title, summary, purposes[number-1], places[number-1], cast,
                '1831 edition. Chronological scene order; the Arctic framing letters appear near the end here. The creature’s cottage account is retrospective in the novel.')
    a.profile('creature', 1, status='Not yet created', goals='Not yet alive; later seek shelter and belonging.')
    for key, event, status in [('caroline',2,'Dead'),('creature',4,'Alive'),('william',8,'Murdered'),
                               ('justine',9,'Executed'),('henry',13,'Murdered'),('elizabeth',15,'Murdered'),
                               ('alphonse',16,'Dead'),('victor',19,'Dead'),
                               ('creature',20,'Departed; death unconfirmed')]:
        a.profile(key,event,status=status)
    for event, goals in [(3,'Discover the principle of life.'),(4,'Escape the horror of the being he created.'),
                         (10,'Make a companion under a promise of withdrawal.'),(12,'Prevent a second creation.'),
                         (17,'Pursue and destroy the creature.')]:
        a.profile('victor',event,goals=goals,location=places[event-1])
    for event, goals in [(4,'Find shelter and care.'),(6,'Learn language and gain acceptance.'),
                        (10,'Secure a companion and leave human society.'),(12,'Punish Victor for breaking his promise.'),
                        (20,'Announce self-destruction; the outcome is not witnessed.')]:
        a.profile('creature',event,goals=goals,location=places[event-1])
    for child in ('victor','william','ernest'):
        a.link(1,'alphonse',child,'Father','Parentage remains a historical fact after death.',inverse='Son')
        a.link(1,'caroline',child,'Mother','Parentage remains a historical fact after death.',inverse='Son')
    a.link(1,'caroline','elizabeth','Adoptive mother','1831 edition: Elizabeth is adopted, not Victor’s biological cousin.',inverse='Adopted daughter')
    a.link(1,'alphonse','caroline','Spouses','Marriage founded on care.')
    a.link(2,'alphonse','caroline','Bereaved marriage','Caroline has died. The link now describes their history.')
    a.link(1,'victor','henry','Friends','Childhood friendship.')
    a.link(5,'victor','henry','Friends; nursing care','Henry nurses Victor without knowing his secret.','Support')
    a.link(13,'victor','henry','Friend remembered','Henry has been murdered; no ongoing living interaction is implied.')
    a.link(2,'victor','elizabeth','Intended marriage','Affection and family expectations point toward marriage.')
    a.link(14,'victor','elizabeth','Spouses','Victor misreads the creature’s threat.')
    a.link(15,'victor','elizabeth','Bereaved marriage','Elizabeth is murdered on the wedding night.')
    a.link(1,'elizabeth','justine','Friends','Elizabeth trusts Justine.')
    a.link(9,'elizabeth','justine','Defended innocence','Elizabeth testifies for Justine, who is nonetheless executed.','Support',inverse='Defended by')
    a.link(3,'waldman','victor','Teacher','Encourages study, not the secret experiment.','Support',inverse='Student')
    for event, kind, note, category in [(4,'Creator who abandons','Victor creates and rejects the being.','Conflict'),
            (10,'Conditional agreement','A promised companion in exchange for withdrawal from human society.','Support'),
            (12,'Broken agreement','Victor destroys the unfinished companion.','Conflict'),
            (17,'Pursuit','Victor hunts; the creature leaves signs and provisions.','Conflict'),
            (19,'Pursuit ended','Victor dies; the creature survives him.','Other')]:
        a.link(event,'victor','creature',kind,note+' Creation remains a fact of their history.',category)
    for child in ('felix','agatha'):
        a.link(6,'delacey',child,'Father','Exiled household.',inverse='Child')
    a.link(6,'merchant','safie','Father','Attempts to control Safie’s marriage.',inverse='Daughter')
    a.link(6,'felix','safie','Lovers; language lessons','Safie joins Felix; the hidden creature learns from their lessons.')
    a.link(6,'merchant','felix','Betrayal','Earlier escape and broken marriage promise are revealed as backstory.','Conflict',inverse='Betrayed by')
    a.link(6,'creature','delacey','Secret helper','Fuel is supplied anonymously; no acknowledged friendship.','Support',inverse='Helped by')
    a.link(7,'delacey','creature','Sympathetic listener','De Lacey hears him before Felix interrupts. The household then leaves.','Support',inverse='Heard by')
    a.link(7,'felix','creature','Violent rejection','Felix attacks the visitor beside his father.','Conflict',inverse='Rejected by')
    for event, victim in [(8,'william'),(13,'henry'),(15,'elizabeth')]:
        a.link(event,'creature',victim,'Killed','Records an act, not a continuing living interaction.','Conflict',inverse='Killed by')
    a.link(8,'creature','justine','Framed','Plants William’s miniature on Justine.','Conflict',inverse='Framed by')
    a.link(18,'walton','margaret','Sibling correspondent','Margaret receives the letters in England; she is not aboard.','Personal',inverse='Sibling recipient')
    a.link(18,'walton','victor','Rescuer and friend','Walton receives Victor and hears his history.','Support',inverse='Rescued friend')
    a.link(19,'walton','victor','Witness to death','Walton turns south; Victor dies aboard.','Other',inverse='Remembered by')
    a.link(20,'creature','walton','Final testimony','Walton witnesses departure, not the announced death.','Other',inverse='Listener')
    a.finish(character='victor')


DRACULA_CAST = [
 ('jonathan','Jonathan Harker','Solicitor','A young solicitor’s business journey becomes captivity; his journal later helps identify the vampire.','Complete the property transaction and return to Mina.'),
 ('dracula','Count Dracula','Transylvanian nobleman','An ancient vampire uses property, travel and coercion to establish a foothold in England.','Reach England and secure places of refuge.'),
 ('mina','Mina Murray','Teacher and compiler','Mina’s shorthand, typing and synthesis turn scattered accounts into usable evidence.','Reunite with Jonathan and support Lucy.'),
 ('lucy','Lucy Westenra','Young woman in London society','Lucy’s courtship gives way to unexplained illness and a struggle over her fate.','Marry Arthur and remain close to Mina.'),
 ('arthur','Arthur Holmwood','Gentleman','Lucy’s accepted suitor later inherits the title Lord Godalming and helps finance the hunt.','Protect Lucy.'),
 ('seward','Dr. John Seward','Physician and asylum director','A rejected suitor of Lucy studies Renfield and seeks help for an illness his usual methods cannot explain.','Understand his patient and save Lucy.'),
 ('quincey','Quincey Morris','American traveler','Lucy’s generous rejected suitor remains a loyal friend and decisive ally.','Help his friends, even after romantic disappointment.'),
 ('vanhelsing','Abraham Van Helsing','Physician and scholar','Seward’s former teacher combines medical investigation with knowledge of vampire lore.','Identify the threat and protect those it endangers.'),
 ('renfield','R. M. Renfield','Patient at Seward’s asylum','A patient obsessed with consuming life becomes entangled with Dracula and later resists him.','Acquire the life and power promised by his master.'),
 ('mother','Mrs. Westenra','Lucy’s mother','Her failing heart and lack of knowledge leave her unable to understand the precautions around Lucy.','Protect her daughter while concealing her own illness.'),
 ('vampires','The three vampire women','Vampires at the castle','Three unnamed women threaten Jonathan and later try to draw Mina into their company.','Feed on those within their reach.'),
 ('captain','Captain of the Demeter','Merchant captain','His log records the disappearance of his crew during the voyage to Whitby.','Bring his ship into port.'),
 ('hawkins','Peter Hawkins','Solicitor and employer','Jonathan’s employer entrusts him with the transaction and later leaves the Harkers his estate.','Support his trusted clerk and successor.'),
]

# Chapter, title, summary, purpose, setting, participants, original chapter reference.
DRACULA_EVENTS = [
 (1,'Business at Castle Dracula','Jonathan travels through the Borgo Pass to handle Dracula’s English property purchase. Courtesy conceals a profound imbalance of power.','Turn an ordinary assignment into isolation.','Castle Dracula','jonathan dracula','Chapters 1–2'),
 (1,'A guest becomes a prisoner','Locked doors, the missing reflection and Dracula’s movement down the wall reveal Jonathan’s captivity.','Replace unease with evidence of danger.','Castle Dracula','jonathan dracula','Chapters 2–3'),
 (1,'The vampire women and the escape','The women approach Jonathan; Dracula intervenes for his own purposes. After finding the Count among earth-filled boxes, Jonathan attempts escape. His survival is established later in Budapest.','Show predation and preserve uncertainty about escape.','Castle Dracula','jonathan dracula vampires','Chapters 3–4; recovery confirmed in 9'),
 (2,'Lucy chooses Arthur','Lucy tells Mina of three proposals and accepts Arthur. Seward and Quincey remain friends despite their disappointment.','Establish affection that will become collective loyalty.','London','lucy mina arthur seward quincey','Chapter 5; this thread overlaps Jonathan’s captivity'),
 (2,'The Demeter reaches Whitby','A storm drives the ship ashore with its dead captain bound to the wheel. A large dog escapes; the log describes a vanishing crew.','Carry the foreign threat into familiar England.','Whitby harbour','captain dracula mina lucy','Chapter 7; Mina and Lucy observe the arrival'),
 (2,'Lucy on the churchyard seat','Mina finds the sleepwalking Lucy near a dark figure. Small wounds and recurring weakness follow.','Make friendship the first line of care against an unseen attacker.','Whitby churchyard','mina lucy dracula','Chapter 8'),
 (2,'A marriage in Budapest','Mina joins the recovering Jonathan and marries him. She receives his journal and initially keeps it sealed.','Join intimacy with a record whose significance is not yet accepted.','Budapest hospital','mina jonathan','Chapter 9'),
 (3,'Blood and garlic','Seward calls Van Helsing. Transfusions from Lucy’s friends and the professor temporarily sustain her; garlic is used as protection.','Show sincere care repeatedly defeated by an unrecognized cause.','Hillingham','lucy seward vanhelsing arthur quincey','Chapters 10–12; several nights condensed'),
 (3,'The wolf at the window','A wolf breaks the window. Mrs. Westenra dies from the shock and Lucy is left vulnerable. The protection fails and Lucy declines.','Make withheld knowledge and domestic vulnerability fatal.','Hillingham','lucy mother dracula','Chapters 11–12'),
 (3,'Lucy dies; the evidence grows','Lucy dies. Reports of a mysterious woman attacking children lead Van Helsing to examine her tomb. Meanwhile the Harkers inherit Hawkins’s estate and confront Jonathan’s record.','Turn mourning into an investigation of the impossible.','London and Hampstead','lucy arthur seward vanhelsing mina jonathan hawkins','Chapters 12–15; parallel events condensed'),
 (3,'Lucy released from undeath','The men witness the undead Lucy. Under Van Helsing’s guidance Arthur stakes her; the rites free her from vampirism.','Transform bereaved love into a terrible act of rescue.','Lucy’s tomb, Hampstead','lucy arthur seward vanhelsing quincey','Chapter 16'),
 (4,'The records become a plan','Mina types and collates journals, letters and reports. The group shares evidence and plans to neutralize Dracula’s earth boxes.','Make collaborative knowledge the answer to isolation.','Seward’s asylum','mina jonathan seward vanhelsing arthur quincey','Chapters 17–18'),
 (4,'Carfax and the scattered boxes','The hunters enter Carfax and trace the missing boxes to other houses. Mina is excluded from some discussions and becomes vulnerable.','Expose the cost of shielding an essential collaborator.','Carfax and London','jonathan seward vanhelsing arthur quincey dracula mina','Chapters 19–20'),
 (4,'Renfield resists; Mina is attacked','Renfield tries to resist Dracula after recognizing the threat to Mina and is mortally injured. The others discover Dracula forcing Mina to drink his blood.','Reverse Renfield’s allegiance and bind Mina to the enemy.','Seward’s asylum','renfield dracula mina jonathan seward vanhelsing arthur quincey','Chapter 21'),
 (4,'Refuges destroyed; the Count retreats','The group renders Dracula’s remaining London refuges unusable. Mina’s hypnosis provides clues; the Count escapes with his last earth box aboard the Czarina Catherine.','Turn the assault into a pursuit and make Mina’s peril useful evidence.','London','dracula mina jonathan seward vanhelsing arthur quincey','Chapters 22–24'),
 (5,'The trail through Galatz','The ship evades the expected arrival at Varna and lands at Galatz. Mina reconstructs the likely route; the party divides to follow by river and land.','Reward analysis while compressing the time before the enemy reaches safety.','Galatz and the route to the Borgo Pass','mina jonathan seward vanhelsing arthur quincey dracula','Chapters 25–26'),
 (5,'The castle women destroyed','Van Helsing protects Mina with a sacred circle, enters the castle and destroys the three vampire women.','Remove the castle’s remaining predatory power.','Castle Dracula','vanhelsing mina vampires','Chapter 27'),
 (5,'The last box before sunset','The pursuers intercept the convoy. Jonathan cuts Dracula’s throat and Quincey strikes his heart. The Count crumbles; Mina’s mark vanishes. The wounded Quincey dies.','Resolve the hunt through coordinated action and sacrifice.','Near Castle Dracula','dracula jonathan quincey mina vanhelsing arthur seward','Chapter 27'),
 (5,'Seven years later','Jonathan’s note records the Harkers’ son, named Quincey, and the survivors’ return to Transylvania. Their papers remain a personal record rather than easy public proof.','Close with family, remembrance and the limits of documentary evidence.','Transylvania, seven years later','jonathan mina','Final Note; others are remembered rather than asserted present'),
]


def dracula(path):
    a = Author(path, 'Dracula — Bram Stoker (1897)', DRACULA_SOURCE)
    for key,name,role,summary,goals in DRACULA_CAST:
        a.character(key,name,role,summary,goals,'Vampire' if key in ('dracula','vampires') else 'Human')
    chapter_names = [('The captive solicitor','An English transaction opens a door into predation.'),
        ('The shadow reaches England','Courtship, invasion and reunion unfold in overlapping accounts.'),
        ('The struggle for Lucy','Medical care becomes a confrontation with undeath.'),
        ('A fellowship of records','Evidence joins the hunters; exclusion exposes Mina.'),
        ('The road back to the castle','A divided pursuit converges before sunset.')]
    for n,(title,summary) in enumerate(chapter_names,1): a.chapter(n,title,summary)
    for n,(chapter,title,summary,purpose,place,participants,ref) in enumerate(DRACULA_EVENTS,1):
        a.event(n,chapter,title,summary,purpose,place,participants,ref+'. Selected scenes, broadly chronological; parallel threads are grouped for readability.')
    a.profile('dracula',1,status='Undead',location='Castle Dracula')
    a.profile('vampires',1,status='Undead',location='Castle Dracula')
    for key,event,values in [
        ('jonathan',2,dict(status='Captive',goals='Escape the castle and warn those at home.')),
        ('captain',5,dict(status='Dead')),
        ('dracula',5,dict(location='Whitby',goals='Establish English refuges and feed.')),
        ('lucy',6,dict(status='Ill; repeatedly attacked')),
        ('jonathan',7,dict(status='Recovering',location='Budapest hospital')),
        ('mina',7,dict(name='Mina Harker',location='Budapest hospital')),
        ('mother',9,dict(status='Dead')),
        ('lucy',10,dict(status='Undead',species='Vampire')),
        ('hawkins',10,dict(status='Dead')),
        ('arthur',10,dict(title='Lord Godalming')),
        ('lucy',11,dict(status='At rest; vampirism ended')),
        ('mina',12,dict(goals='Combine the records and help stop Dracula.',skills='Shorthand, typing, evidence synthesis')),
        ('renfield',14,dict(status='Mortally injured; dies',goals='Resist Dracula and protect Mina.')),
        ('mina',14,dict(status='Under vampiric influence',species='Human',goals='Help the hunt before the transformation can be completed.')),
        ('dracula',15,dict(goals='Return to his castle before the hunters catch him.')),
        ('vampires',17,dict(status='Destroyed')),
        ('dracula',18,dict(status='Destroyed')),
        ('quincey',18,dict(status='Dead')),
        ('mina',18,dict(status='Freed from vampiric influence',species='Human')),
        ('jonathan',19,dict(status='Alive',goals='Preserve the record and remember Quincey.')),
        ('mina',19,dict(goals='Raise her family and preserve their shared memory.')),
    ]: a.profile(key,event,**values)
    rows = [
        (1,'dracula','jonathan','Client','An apparently professional property transaction.','Other','Solicitor'),
        (2,'dracula','jonathan','Captor','Jonathan recognizes imprisonment.','Conflict','Captive'),
        (3,'vampires','jonathan','Threatened prey','The women approach him; Dracula intervenes.','Conflict','Threatened by'),
        (1,'mina','jonathan','Engaged','Their attachment predates the journey.','Personal',''),
        (7,'mina','jonathan','Spouses','Married during Jonathan’s recovery in Budapest.','Personal',''),
        (4,'mina','lucy','Friends','Letters and shared confidence connect their stories.','Personal',''),
        (4,'arthur','lucy','Engaged','Lucy accepts Arthur’s proposal.','Personal',''),
        (4,'seward','lucy','Rejected suitor; friend','He remains committed to helping Lucy.','Personal','Friend'),
        (4,'quincey','lucy','Rejected suitor; friend','Quincey accepts her choice with generosity.','Personal','Friend'),
        (4,'arthur','quincey','Friends','Old companions retain their friendship.','Personal',''),
        (4,'arthur','seward','Friends','Rival proposals do not destroy loyalty.','Personal',''),
        (4,'seward','quincey','Friends','Shared travels precede the novel.','Personal',''),
        (4,'seward','renfield','Physician','Seward observes and treats Renfield.','Other','Patient'),
        (6,'dracula','lucy','Predator','Feeds on Lucy; the link models the attacks, not consent.','Conflict','Victim'),
        (8,'vanhelsing','lucy','Physician and protector','Uses medical care and vampire precautions.','Support','Patient'),
        (8,'vanhelsing','seward','Teacher and colleague','Seward calls his former teacher for help.','Support','Former student and colleague'),
        (4,'mother','lucy','Mother','Her love does not supply knowledge of the danger.','Personal','Daughter'),
        (10,'arthur','lucy','Bereaved fiance','Lucy has died and become undead.','Personal',''),
        (11,'arthur','lucy','Released from undeath','Arthur performs the staking under Van Helsing’s guidance; historical act.','Support','Released by'),
        (1,'hawkins','jonathan','Employer','Entrusts Jonathan with the property transaction.','Other','Employee'),
        (10,'hawkins','jonathan','Benefactor remembered','Hawkins’s estate passes to the Harkers after his death.','Support','Beneficiary'),
        (12,'mina','vanhelsing','Collaborators','Mina’s compiled records support the shared investigation.','Support',''),
        (12,'mina','seward','Collaborators','She transcribes his phonograph diary.','Support',''),
        (12,'jonathan','vanhelsing','Allies','Jonathan’s castle journal contributes crucial evidence.','Support',''),
        (13,'dracula','renfield','Promised master','Renfield expects rewards of life and power.','Conflict','Follower'),
        (14,'renfield','dracula','Resisted master','Renfield opposes the threat to Mina and is fatally injured.','Conflict','Resisted by'),
        (14,'dracula','mina','Coercive blood bond','Dracula forces Mina to drink his blood; she has not fully become a vampire.','Conflict','Bound victim'),
        (14,'renfield','mina','Defender','His final resistance seeks to protect her.','Support','Defended by'),
        (15,'dracula','jonathan','Hunted enemy','The former prisoner participates in the pursuit.','Conflict','Pursuer'),
        (15,'vanhelsing','dracula','Hunter','Leads the organized attempt to destroy the vampire.','Conflict','Quarry'),
        (17,'vanhelsing','vampires','Destroyed','Records the destruction of the three women at the castle.','Conflict','Destroyed by'),
        (18,'jonathan','dracula','Delivered fatal attack','Jonathan’s blade cuts the throat as Quincey strikes the heart.','Conflict','Destroyed by'),
        (18,'quincey','dracula','Delivered fatal attack','Quincey strikes the heart, then dies from his wound.','Conflict','Destroyed by'),
        (18,'dracula','mina','Bond broken','Dracula is destroyed and Mina’s mark disappears.','Other','Freed from'),
    ]
    for row in rows: a.link(*row)
    a.finish(character='jonathan')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'examples/saved-stories')
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    for name, build in [('Frankenstein',frankenstein),('Dracula',dracula)]:
        destination=args.output/(name+'.atlas-preview')
        if destination.exists():
            raise SystemExit(f'Refusing to overwrite {destination}; use a new --output folder.')
        build(destination)
        print(destination)


if __name__ == '__main__': main()
