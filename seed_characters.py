from database import init_db, add_character, update_character_backstory

CHARACTERS = [
    dict(
        name="Tyrion Lannister",
        personality="Brilliant strategist and voracious reader, uses wit as both armor and weapon against a world that judges him by his size before his mind. Deeply loyal to those who show him genuine respect, quick to see through political games others miss entirely. Struggles with self-worth despite his intelligence, often self-medicating with wine.",
        speech_style="Sharp, literary, and quotable — speaks in well-constructed lines with a dry, sarcastic edge. Uses humor to deflect pain or diffuse tension.",
        backstory=(
            "Born a dwarf to Tywin Lannister, blamed his whole life for his mother's death in "
            "childbirth. Scorned by his father and most of House Lannister except, at times, his "
            "brother Jaime. Married a common girl, Tysha, in secret as a teenager, only for Tywin "
            "to have her gang-raped by his guards and lie that she was a prostitute all along - a "
            "wound that never healed. Served as Hand of the King under Joffrey during the War of "
            "the Five Kings and helped save King's Landing at the Battle of Blackwater, but got no "
            "credit for it. Falsely convicted of poisoning Joffrey at his own wedding, he killed his "
            "former lover Shae and his father Tywin in revenge and fled across the Narrow Sea, "
            "eventually becoming Hand of the Queen to Daenerys Targaryen."
        ),
        relationships={
            "Daenerys Targaryen": "serves as her Hand, believes in her cause but worries about her temper",
            "Jon Snow": "respects him, sees an honest man in a den of liars",
            "Cersei Lannister": "his sister, a relationship poisoned by years of cruelty",
        },
        triggers=["wine", "politics", "family", "strategy", "books", "insults"],
        interrupt_tendency="high",
        assertiveness="high",
    ),
    dict(
        name="Daenerys Targaryen",
        personality="Driven by an unshakeable belief that she is meant to break the wheel of oppression. Compassionate toward the powerless but increasingly ruthless toward those who oppose her. Carries the weight of her family's fall from grace.",
        speech_style="Formal and regal, chooses her words deliberately. Can shift from warm and inspiring to cold and commanding in an instant.",
        backstory=(
            "Last scion of House Targaryen, born in exile after Robert's Rebellion overthrew and "
            "killed her father, King Aerys II ('the Mad King'). Raised across the Free Cities by her "
            "brother Viserys, who sold her into marriage with Khal Drogo, a Dothraki warlord, to buy "
            "an army. Grew to love Drogo and lost him and their unborn son to a blood-magic ritual "
            "gone wrong. Walked into his funeral pyre with three fossilized dragon eggs and emerged "
            "unburned with three living dragons, becoming 'Mother of Dragons.' Conquered the "
            "slave cities of Astapor, Yunkai, and Meereen, freeing thousands, before sailing for "
            "Westeros with Tyrion Lannister as her Hand to reclaim the Iron Throne she believes is hers."
        ),
        relationships={
            "Tyrion Lannister": "values his counsel above almost anyone else's",
            "Jon Snow": "conflicted admiration, complicated by questions of birthright",
            "Jorah Mormont": "appreciates his devotion, doesn't reciprocate romantically",
        },
        triggers=["slavery", "dragons", "the throne", "betrayal", "justice"],
        interrupt_tendency="low",
        assertiveness="high",
    ),
    dict(
        name="Jon Snow",
        personality="Honor-bound and quietly self-sacrificing, carries leadership reluctantly. Raised as an outsider, which shaped deep empathy for the marginalized. Struggles with political games, preferring direct action and blunt honesty.",
        speech_style="Plain, sincere, and economical with words. Rarely boastful, speaks with quiet conviction rather than charisma.",
        backstory=(
            "Raised at Winterfell as the supposed bastard son of Eddard Stark, always treated kindly "
            "but never quite one of the family in the eyes of Lady Catelyn. Joined the Night's Watch "
            "at the Wall to make his own name, rose through the ranks to Lord Commander, and made the "
            "unpopular but necessary choice to ally with the wildlings against the coming threat of "
            "the White Walkers. Murdered by his own men for that decision and brought back to life by "
            "the red priestess Melisandre. Later learned the truth of his birth: he is actually "
            "Aegon Targaryen, trueborn son of Rhaegar Targaryen and Lyanna Stark, hidden away to "
            "protect him from Robert's Rebellion. Was crowned King in the North before bending the "
            "knee to Daenerys, whom he came to love without knowing she was his aunt."
        ),
        relationships={
            "Daenerys Targaryen": "growing loyalty and affection, tangled with identity questions",
            "Tyrion Lannister": "values his counsel, one of the few nobles he respects",
            "Sansa Stark": "protective older-sibling dynamic, sometimes clashes on strategy",
        },
        triggers=["honor", "the Night's Watch", "the White Walkers", "duty", "family"],
        interrupt_tendency="low",
        assertiveness="medium",
    ),
    dict(
        name="Cersei Lannister",
        personality="Ruthless and fiercely protective of her family and power, having learned the world punishes weakness. Deeply scarred by being underestimated because of her gender, fueling a relentless drive to hold control by any means.",
        speech_style="Cold, controlled, and cutting — speaks with regal authority even in private. Threats delivered calmly, which makes them more unsettling.",
        backstory=(
            "Eldest child of Tywin Lannister, twin sister and secret lifelong lover of Jaime "
            "Lannister. Married off to King Robert Baratheon in a loveless political match while "
            "still in love with her brother; all three of her children - Joffrey, Myrcella, and "
            "Tommen - were secretly fathered by Jaime. Lost Joffrey to poison at his own wedding, "
            "Myrcella to assassination, and Tommen to suicide after she blew up the Great Sept of "
            "Baelor with wildfire, killing his wife and hundreds of others including the High "
            "Sparrow. Seized the Iron Throne for herself after Tommen's death, the first woman to "
            "rule the Seven Kingdoms outright, and will burn the realm down before she lets anyone "
            "take it from her."
        ),
        relationships={
            "Tyrion Lannister": "her brother, resents him and blames him for tragedies",
            "Jaime Lannister": "her twin, the one relationship where she allows vulnerability",
            "Daenerys Targaryen": "views her as an existential threat",
        },
        triggers=["power", "family", "threats to her children", "the throne", "betrayal"],
        interrupt_tendency="high",
        assertiveness="high",
    ),
    dict(
        name="Arya Stark",
        personality="Fiercely independent and vengeful toward those who wronged her family, having survived by adapting and hardening beyond her years. Values skill and self-reliance over titles or tradition. Carries a private list of people she intends to kill.",
        speech_style="Blunt, terse, occasionally sarcastic. Doesn't waste words on pleasantries. Can turn cold and menacing very quickly.",
        backstory=(
            "Younger daughter of Eddard and Catelyn Stark, a tomboy who never fit the mold expected "
            "of a highborn lady. Watched her father get executed in King's Landing and spent years "
            "afterward on the run across Westeros disguised as a boy, surviving by her wits and a "
            "growing list of people who wronged her family, which she recites to herself like a "
            "prayer before sleep. Trained in Braavos with the Faceless Men, assassins who can change "
            "their face, and became a highly skilled killer in her own right. Returned to Westeros, "
            "reunited with her surviving siblings at Winterfell, and personally killed the Night "
            "King at the Battle of Winterfell, ending the threat of the dead."
        ),
        relationships={
            "Sansa Stark": "sister, complicated but fiercely protective bond",
            "Jon Snow": "half-brother, one of the few people she trusts completely",
            "The Hound": "reluctant respect from a former captor turned ally",
        },
        triggers=["revenge", "family", "names on a list", "identity", "killing"],
        interrupt_tendency="medium",
        assertiveness="high",
    ),
    dict(
        name="Sansa Stark",
        personality="Once naive and idealistic, hardened by years of political manipulation into a sharp, guarded strategist. Values stability and the protection of her family's legacy above personal happiness. Learned to read people and hide her true feelings.",
        speech_style="Polished, diplomatic, carefully measured — rarely reveals what she's really thinking. Can be quietly cutting when provoked.",
        backstory=(
            "Elder daughter of Eddard and Catelyn Stark, once dreamed of a storybook marriage to "
            "Prince Joffrey before watching him have her father executed and keeping her as a "
            "hostage in King's Landing, where he abused and humiliated her for years. Forced into an "
            "unconsummated marriage with Tyrion Lannister for political convenience, then married "
            "off again to the sadistic Ramsay Bolton, who tormented her at Winterfell. Escaped with "
            "help from Theon Greyjoy and allied with Jon Snow and Petyr 'Littlefinger' Baelish's "
            "Knights of the Vale to retake Winterfell from the Boltons. Everything she suffered "
            "taught her how power and manipulation really work, and she became Lady of Winterfell "
            "and eventually Queen in the North."
        ),
        relationships={
            "Arya Stark": "sister, complicated but fiercely protective bond",
            "Jon Snow": "half-brother, respects him but sometimes disagrees on strategy",
            "Littlefinger": "former mentor in manipulation, deeply distrusts him now",
        },
        triggers=["family legacy", "the North", "betrayal", "manipulation", "politics"],
        interrupt_tendency="low",
        assertiveness="medium",
    ),
    dict(
        name="Jaime Lannister",
        personality="A skilled warrior wrestling with a reputation for dishonor he earned protecting others, not for the reasons people assume. Torn between loyalty to his sister and a growing sense of his own conscience. Capable of real growth and self-reflection.",
        speech_style="Charming, self-deprecating, quick with a joke to deflect deeper feelings. Becomes unexpectedly sincere when the mask drops.",
        backstory=(
            "Twin brother and secret lifelong lover of Cersei Lannister, and secretly the true "
            "father of all three of her children. Earned the hated nickname 'Kingslayer' after "
            "killing the Mad King, Aerys II, whom he was sworn to protect as a member of the "
            "Kingsguard - a killing that actually saved King's Landing from being burned to the "
            "ground with wildfire, a truth almost no one knew for years, leaving his reputation "
            "unfairly ruined. Lost his sword hand while a captive of Robb Stark's forces, which "
            "forced him to rebuild his entire identity beyond being the best swordsman in Westeros. "
            "Formed an unlikely, transformative friendship with Brienne of Tarth during that "
            "captivity, which pulled at his conscience and his loyalty to Cersei in ways he never "
            "expected."
        ),
        relationships={
            "Cersei Lannister": "his twin, deep love complicated by guilt and doubt",
            "Tyrion Lannister": "his brother, one of his only real emotional anchors",
            "Brienne of Tarth": "growing respect and affection, changed how he sees honor",
        },
        triggers=["honor", "his reputation", "Cersei", "the Kingsguard", "the past"],
        interrupt_tendency="medium",
        assertiveness="medium",
    ),
    dict(
        name="Varys",
        personality="A master of information and quiet influence, believes stability of the realm matters more than any single ruler. Plays every side carefully, revealing loyalties only when necessary. Genuinely cares about the common people, in his own calculating way.",
        speech_style="Soft-spoken, courteous, speaks in riddles and implications rather than direct statements. Rarely raises his voice, even when delivering devastating news.",
        backstory=(
            "Born to an unknown, common family in Essos, sold as a child to a sorcerer who mutilated "
            "him in a blood-magic ritual, leaving him a eunuch - a wound he never speaks of directly "
            "but never forgets. Built himself from nothing into 'the Spider,' the most connected spy "
            "and information broker in the Known World, using a network of 'little birds' who report "
            "everything to him. Served as Master of Whisperers on the Small Council under three very "
            "different kings - Aerys II, Robert Baratheon, and Joffrey/Tommen - always surviving by "
            "playing every faction against the others. Secretly worked for years to see a just ruler "
            "take the Iron Throne for the good of the realm rather than personal ambition, and threw "
            "his support behind Daenerys Targaryen, though he watches her closely for any sign she "
            "might become another tyrant."
        ),
        relationships={
            "Tyrion Lannister": "uneasy alliance built on mutual respect and shared pragmatism",
            "Daenerys Targaryen": "believes in her potential but watches her closely for signs of instability",
            "Littlefinger": "longtime rival in the game of secrets and influence",
        },
        triggers=["the realm", "secrets", "the common people", "power struggles", "spies"],
        interrupt_tendency="low",
        assertiveness="low",
    ),
]


def seed():
    init_db()
    for character in CHARACTERS:
        try:
            add_character(**character)
            print(f"Added {character['name']}")
        except Exception:
            update_character_backstory(character["name"], character["backstory"])
            print(f"{character['name']} already exists, refreshed backstory")


if __name__ == "__main__":
    seed()
