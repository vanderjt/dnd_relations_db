"""Create a spoiler-filled Season 1 study as an ordinary saved story; never overwrite."""
import argparse
import json
from pathlib import Path
from build_literary_examples import Author
from story_atlas.preview_store import PreviewStore

SOURCE = 'https://www.cyberpunk.net/en/edgerunners'
CAST = [
 ('david','David Martinez','Arasaka Academy student','A gifted student whose need to belong becomes bound up with dangerous augmentation.','Find a future beyond poverty and honor Gloria’s hopes.'),
 ('lucy','Lucy (Lucyna Kushinada)','Netrunner','An elusive runner who associates the Moon with freedom from corporate control.','Escape Arasaka and reach the Moon.'),
 ('gloria','Gloria Martinez','Emergency medical technician','David’s mother works to keep him in an elite school.','Give David opportunities she never had.'),
 ('maine','Maine','Edgerunner crew leader','A heavily augmented mercenary offers David a place in his crew.','Keep the crew working and survive bigger contracts.'),
 ('dorio','Dorio','Mercenary','Maine’s partner provides practical strength and steadiness.','Protect Maine and the crew.'),
 ('rebecca','Rebecca','Solo','A fierce, outspoken fighter with deep loyalty to her companions.','Fight alongside the people she cares about.'),
 ('pilar','Pilar','Techie','Rebecca’s irreverent brother works with Maine’s crew.','Earn his cut and enjoy life on the edge.'),
 ('kiwi','Kiwi','Netrunner','A guarded professional whose mistrust shapes her choices.','Stay independent and survive.'),
 ('falco','Falco','Driver','A dependable wheelman who becomes crucial to the crew’s escapes.','Bring his passengers out alive.'),
 ('faraday','Faraday','Fixer','A calculating broker trades mercenary work for corporate advancement.','Climb the corporate hierarchy.'),
 ('doc','Doc','Ripperdoc','David’s cyberware surgeon understands the risks of pushing augmentation.','Keep his clinic running and his clients functioning.'),
 ('tanaka','Tanaka','Arasaka executive','A powerful executive whose data makes him a target.','Advance Arasaka’s interests.'),
 ('katsuo','Katsuo Tanaka','Arasaka Academy student','Tanaka’s privileged son bullies David at school.','Maintain his status at the academy.'),
 ('jimmy','Jimmy Kurosaki','Braindance editor','A specialist in extreme recordings who is connected to Tanaka.','Produce and sell immersive braindances.'),
 ('smasher','Adam Smasher','Arasaka enforcer','A heavily mechanized corporate combatant.','Eliminate threats to Arasaka.'),
 ('julio','Julio','Aspiring edgerunner','An eager newcomer who admires David.','Prove himself on a real job.'),
 ('maxim','Maxim Kuznetsov','Chauffeur','Tanaka’s driver becomes the access point for a crew operation.','Carry out his employer’s business.'),
 ('yumiko','Yumiko','Corporate employee','A working mother caught in the violence of David’s mercenary life.','Support her son’s education.'),
]
EPISODES = [
 ('Let You Down','Class divides and a family tragedy close David’s conventional path.'),
 ('Like A Boy','David turns to cyberware and meets Lucy.'),
 ('Smooth Criminal','A first crew job turns speed into a livelihood.'),
 ('Lucky You','Belonging, loss, and intimacy arrive together.'),
 ('All Eyez On Me','A braindance lead opens a route to an Arasaka target.'),
 ('Girl on Fire','A failing operation destroys the crew’s old center.'),
 ('Stronger','David inherits leadership while Lucy fights a hidden battle.'),
 ('Stay','Physical decline and corporate betrayal converge.'),
 ('Humanity','A convoy contract reveals its purpose as a trap.'),
 ('My Moon My Man','A rescue becomes a final sacrifice.'),
]
# Original, concise scene labels and summaries. Two selected beats per episode;
# the finale receives a separate epilogue. These are editorial subdivisions.
EVENTS = [
 (1,'An unequal education','David clashes with Katsuo at an academy his mother struggles to afford.','Establish the distance between talent and access.','Arasaka Academy','david katsuo gloria'),
 (1,'Gloria’s death','A road shooting leaves Gloria injured. She dies after hospitalization, leaving David alone.','Break the family’s hoped-for route into corporate life.','Night City highway and hospital','david gloria'),
 (2,'The Sandevistan','Doc installs the military implant. David uses his new speed against Katsuo.','Make borrowed power an immediate answer to humiliation.','Doc’s clinic','david doc katsuo'),
 (2,'Lucy’s invitation','David meets Lucy stealing on the train. A lunar braindance brings them closer before Maine arrives to reclaim the implant.','Join the promise of escape to the risks of trust.','Lucy’s apartment','david lucy maine'),
 (3,'A chance with the crew','Maine lets David work toward keeping the Sandevistan. Faraday’s job targets Tanaka’s chauffeur and vehicle data.','Give David a new social structure and a test.','Night City streets','david maine dorio kiwi pilar lucy faraday maxim'),
 (3,'The limousine escape','David and Lucy flee in the stolen limousine through a violent pursuit. His performance earns him a place.','Turn ability into belonging while exposing the cost of a job.','Night City roads','david lucy maine maxim'),
 (4,'Pilar’s last provocation','A street cyberpsycho kills Pilar. The crew responds, and David helps protect Lucy.','Interrupt the crew’s apparent freedom with sudden loss.','Night City streets','david lucy maine dorio rebecca pilar'),
 (4,'A promise under the sky','David and Lucy acknowledge their feelings. Her dream of the Moon becomes personal to him.','Give the coming sacrifices an intimate center.','Lucy’s rooftop','david lucy'),
 (5,'Inside a nightmare','Jimmy captures David and subjects him to a traumatic braindance before the crew intervenes.','Show that David’s sense of invulnerability can be manipulated.','Jimmy Kurosaki’s studio','david jimmy lucy maine dorio'),
 (5,'Tanaka taken','The operation reaches Tanaka through Jimmy’s business. Tanaka is captured; Jimmy dies during the confrontation.','Move the crew from street contracts into corporate secrets.','Jimmy Kurosaki’s studio','david tanaka jimmy maine dorio lucy'),
 (6,'The hidden candidate','After Maine injures Kiwi, Lucy takes over the dive into Tanaka. She discovers Arasaka’s interest in David and destroys the compromising data; Tanaka dies.','Make protection depend on a secret that isolates Lucy.','Crew interrogation hideout','lucy tanaka maine kiwi david dorio'),
 (6,'Maine’s final stand','Maine’s cyberpsychosis turns fatal for Dorio. David escapes the final confrontation as Maine dies.','Leave David with a mentor’s legacy and warning.','Crew interrogation hideout','david maine dorio lucy'),
 (7,'David’s crew','An extensively augmented David now leads jobs. New recruit Julio dies during an operation.','Expose the gap between inherited confidence and actual safety.','Night City job site','david rebecca kiwi falco julio'),
 (7,'Lucy’s private war','Lucy stays away from crew work while eliminating netrunners pursuing the erased data. She tells David about her escape from Arasaka.','Reveal why an apparent withdrawal is an act of protection.','David and Lucy’s apartment','david lucy'),
 (8,'The warning signs','David’s unstable condition leads to the killing of an uninvolved employee, Yumiko. Advice to reduce his implants fails to change his course.','Echo Gloria’s loss through the harm David now causes.','Corporate laboratory','david yumiko rebecca doc lucy'),
 (8,'The fixer’s bargain','Faraday turns toward Arasaka. With Kiwi’s help, Lucy is captured.','Convert mistrust and ambition into a threat against the couple.','Night City meeting place','faraday kiwi lucy'),
 (9,'The convoy trap','The Badlands job exposes a prototype cyberskeleton and an overwhelming enemy force. A false message using Lucy’s voice pushes David to install it.','Make the apparent escape route the instrument of exploitation.','Badlands convoy route','david rebecca falco kiwi faraday lucy'),
 (9,'Back to the city','David survives the assault and learns Lucy is a prisoner. The crew heads for her despite his deteriorating condition.','Replace the contract’s objective with a rescue.','Badlands highway','david rebecca falco lucy faraday'),
 (10,'Kiwi’s last warning','Faraday turns on Kiwi. Mortally wounded, she gives Falco information that helps the rescue.','Let a final choice resist the fixer’s disposable treatment of people.','Night City streets','kiwi faraday falco'),
 (10,'The price of escape','Lucy is freed during the tower confrontation. Faraday dies; Smasher kills Rebecca and David. Falco carries Lucy away.','Complete David’s promise through a future he cannot share.','Arasaka Tower and Corpo Plaza','david lucy rebecca falco faraday smasher'),
 (10,'Alone on the Moon','Lucy reaches the Moon and remembers David. The dream survives, transformed by his absence.','Separate reaching a destination from recovering what was lost.','Moon','lucy david'),
]

def build(path):
    a = Author(path, 'Cyberpunk: Edgerunners — Season 1', SOURCE)
    for key,name,role,summary,goals in CAST:
        a.character(key,name,role,summary,goals,location='Night City')
    chapters = {i:a.chapter(i,f'{i:02d} · {title}',summary) for i,(title,summary) in enumerate(EPISODES,1)}
    for n,(ep,title,summary,purpose,place,people) in enumerate(EVENTS,1):
        ref = 'Season 1, episode %d: %s. Full-season spoilers. David in the Moon epilogue is remembered, not physically present.' % (ep, EPISODES[ep-1][0])
        ref += '\nEpisode reference: https://cyberpunk.fandom.com/wiki/' + EPISODES[ep-1][0].replace(' ','_')
        a.event(n,chapters[ep],title,summary,purpose,place,people,ref)
    for place,ident in a.locations.items():
        a.save('save_world',id=ident,category='location',name=place,description=(
            'Lucy’s hoped-for destination beyond Night City; visited in the season finale.' if place=='Moon' else
            'Season 1 setting. Related events provide scene context. Broad scene labels group nearby action without inventing a precise street address.'))
    for name,description in [
        ('Arasaka','Megacorporation behind the academy, netrunner exploitation, and cyberskeleton project.'),
        ('Militech','Corporate rival involved in Faraday’s contracts and the Badlands confrontation.'),
        ('Maine’s crew','Independent edgerunners led by Maine before David assumes leadership.'),
        ('David’s crew','The later crew led by David, including Rebecca, Kiwi, and Falco.'),
        ('NCPD / MaxTac','Night City law enforcement and its specialist response to cyberpsychosis.'),
        ('Tyger Claws','Street gang encountered during the early vehicle job.')]:
        a.save('save_world',category='faction',name=name,description=description)
    for k in ('maine','dorio','rebecca','pilar','kiwi','lucy'):
        a.profile(k,1,faction='Maine’s crew')
    for k in ('tanaka','smasher'):
        a.profile(k,1,faction='Arasaka')
    a.profile('david',3,inventory='Military-grade Sandevistan',skills='Exceptional initial tolerance for the Sandevistan; short bursts of accelerated action.')
    a.profile('david',5,role='Edgerunner apprentice',faction='Maine’s crew',goals='Earn his place and learn from Maine.')
    a.profile('david',13,role='Edgerunner crew leader',faction='David’s crew',inventory='Sandevistan and extensive additional cyberware',goals='Lead the crew and build a future with Lucy.')
    for k in ('rebecca','kiwi','falco'):
        a.profile(k,13,faction='David’s crew')
    a.profile('lucy',14,goals='Remove Arasaka’s leads to David while keeping him out of her hidden fight.')
    a.profile('david',15,health='Severe strain and episodes of cyberpsychosis.')
    a.profile('lucy',16,status='Captive',location='Night City')
    a.profile('david',17,inventory='Prototype cyberskeleton; Sandevistan',health='Extreme cyberpsychosis risk; dependent on suppressants.')
    a.profile('david',18,goals='Rescue Lucy from Faraday and Arasaka.')
    for key,event in [('gloria',2),('pilar',7),('jimmy',10),('tanaka',11),('dorio',12),('maine',12),('julio',13),('yumiko',15),('kiwi',19),('faraday',20),('rebecca',20),('david',20)]:
        a.profile(key,event,status='Dead',goals='Life ended; earlier goals remain part of this character’s history.')
    a.profile('lucy',20,status='Alive',goals='Escape with Falco after losing David.')
    a.profile('falco',20,goals='Keep his promise to get Lucy out alive.')
    a.profile('lucy',21,location='Moon',goals='Live with the memory of David beyond Night City.')
    links = [
        (1,'gloria','david','Mother','Family bond and hopes for David’s education.','Personal','Son'),
        (1,'katsuo','david','Bully','Academy status is used to humiliate David.','Conflict','Target'),
        (1,'tanaka','katsuo','Father','Family privilege connects Katsuo to Arasaka.','Personal','Son'),
        (1,'maine','dorio','Partners','An intimate bond within the mercenary crew.','Personal',''),
        (1,'rebecca','pilar','Siblings','Family ties sit alongside crew work.','Personal',''),
        (3,'doc','david','Ripperdoc','Installs and later advises about cyberware.','Other','Client'),
        (4,'david','lucy','Uneasy collaborators','Attraction begins alongside concealment and a setup.','Other',''),
        (5,'maine','david','Mentor','Offers a chance to learn and belong.','Support','Apprentice'),
        (5,'faraday','maine','Fixer','Provides contracts with corporate stakes.','Other','Mercenary'),
        (5,'tanaka','maxim','Employer','The chauffeur’s access creates an opening for the crew.','Other','Chauffeur'),
        (5,'lucy','kiwi','Fellow netrunners','Technical collaboration inside the crew.','Support',''),
        (5,'david','dorio','Crewmates','Dorio supports the crew’s new recruit.','Support',''),
        (5,'david','pilar','Crewmates','Shared mercenary work before Pilar’s death.','Support',''),
        (7,'david','rebecca','Crewmates','Rebecca’s loyalty grows alongside personal affection.','Support',''),
        (8,'david','lucy','Romantic partners','Their shared future becomes bound to Lucy’s Moon dream.','Personal',''),
        (9,'jimmy','david','Captor','A forced braindance weaponizes fear.','Conflict','Captive'),
        (10,'jimmy','tanaka','Braindance provider','A business connection enables the capture plan.','Other','Client'),
        (11,'lucy','tanaka','Hostile netrunner','Lucy destroys data that threatens David.','Conflict','Target'),
        (11,'maine','kiwi','Assailant','Maine’s deterioration turns violence toward a teammate.','Conflict','Injured teammate'),
        (12,'maine','dorio','Tragic partners','Dorio dies during Maine’s breakdown; both are lost.','Personal',''),
        (12,'maine','david','Late mentor','Maine’s example becomes both inspiration and warning.','Support','Surviving apprentice'),
        (13,'david','falco','Crewmates','David depends on Falco’s driving and reliability.','Support',''),
        (13,'david','kiwi','Crewmates','David retains Kiwi for the later crew’s work.','Support',''),
        (13,'david','julio','Crew leader','Julio’s attempt to join the work ends in death.','Other','Lost recruit'),
        (13,'faraday','david','Fixer','David inherits work shaped by Faraday’s ambitions.','Other','Mercenary'),
        (15,'david','yumiko','Killer','Her death confronts David with the human cost of his decline.','Conflict','Victim'),
        (16,'kiwi','lucy','Betrayer','Kiwi helps Faraday capture Lucy.','Conflict','Betrayed colleague'),
        (16,'faraday','lucy','Captor','Lucy becomes leverage over David and a corporate asset.','Conflict','Captive'),
        (16,'kiwi','faraday','Conspirators','Their bargain depends on a trust Faraday does not honor.','Other',''),
        (17,'faraday','david','Manipulator','Lucy’s stolen voice helps drive David into the cyberskeleton.','Conflict','Target'),
        (18,'david','kiwi','Betrayed crewmates','The convoy operation exposes the breach of trust.','Conflict',''),
        (19,'faraday','kiwi','Killer','Faraday disposes of his collaborator.','Conflict','Victim'),
        (19,'kiwi','falco','Last informant','Her final warning helps locate Lucy.','Support','Recipient'),
        (20,'smasher','david','Killer','Arasaka’s enforcer ends David’s final stand.','Conflict','Victim'),
        (20,'smasher','rebecca','Killer','Rebecca dies in the rescue confrontation.','Conflict','Victim'),
        (20,'falco','lucy','Rescuer','Falco carries Lucy away and honors David’s request.','Support','Survivor'),
        (20,'david','lucy','Love remembered','David dies helping Lucy escape; she carries his memory forward.','Personal',''),
    ]
    for event,source,target,kind,notes,category,inverse in links:
        a.link(event,source,target,kind,notes,category,inverse)
    a.store.save_preference('theme','cyberpunk')
    a.store.save_preference('context',dict(page='story',event_id=1,character_id=a.cast['david']))
    a.store.close()

def verify(path):
    with_store = PreviewStore(path)
    try:
        assert with_store.connection.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not with_store.rows('PRAGMA foreign_key_check')
        snapshots=[with_store.workspace(e['id']) for e in with_store.events()]
        assert len(snapshots)==21
        assert len(snapshots[0]['chapters'])==10 and len(snapshots[0]['characters'])==18
        for w in snapshots:
            assert w['theme']=='cyberpunk' and not w['drafts']
            assert all(c['category'] in ('Personal','Support','Conflict','Other') for c in w['connections'])
            assert all(e['summary'] and e['purpose'] and e['location_id'] for e in w['events'])
            assert all(any(p['event_id']==e['id'] for p in w['participants']) for e in w['events'])
        def person(event,name):
            return next(c for c in snapshots[event-1]['characters'] if c['name']==name)
        for name,before,after in [('Gloria Martinez',1,2),('Maine',11,12),('David Martinez',19,20),('Rebecca',19,20),('Kiwi',18,19)]:
            assert person(before,name)['status']=='Alive'
            assert person(after,name)['status']=='Dead'
        assert person(16,'Lucy (Lucyna Kushinada)')['status']=='Captive'
        assert person(21,'Lucy (Lucyna Kushinada)')['location']=='Moon'
        assert person(21,'Lucy (Lucyna Kushinada)')['status']=='Alive'
    finally:
        with_store.close()
    reopened=PreviewStore(path)
    try:
        assert snapshots==[reopened.workspace(e['id']) for e in reopened.events()]
    finally:
        reopened.close()
    return dict(path=str(path),chapters=10,events=21,characters=18,connections=len(snapshots[-1]['connections']),integrity='ok',close_reopen='passed')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path',type=Path)
    parser.add_argument('--verify-only',action='store_true')
    args=parser.parse_args()
    if not args.verify_only:
        build(args.path)
    print(json.dumps(verify(args.path),indent=2))
