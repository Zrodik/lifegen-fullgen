from __future__ import annotations
from random import choice, randint, sample, random, choices, getrandbits, randrange, shuffle
from typing import Dict, List, Any
import os.path
import itertools
import sys

from .history import History
from .skills import CatSkills
from ..housekeeping.datadir import get_save_dir
from ..events_module.generate_events import GenerateEvents

import ujson

from .names import Name
from .pelts import Pelt
from .genotype import Genotype
from .phenotype import Phenotype
from scripts.conditions import Illness, Injury, PermanentCondition, get_amount_cat_for_one_medic, \
    medical_cats_condition_fulfilled
import bisect
#from scripts.events_module.condition_events import Condition_Events
from scripts.utility import get_med_cats, get_personality_compatibility, event_text_adjust, update_sprite, \
    leader_ceremony_text_adjust, get_cluster
from scripts.game_structure.game_essentials import game, screen
from scripts.cat_relations.relationship import Relationship
from scripts.game_structure import image_cache
from scripts.event_class import Single_Event
from .thoughts import Thoughts
from scripts.cat_relations.inheritance import Inheritance


class Cat():
    dead_cats = []
    used_screen = screen
    
    
    ages = [
        'newborn', 'kitten', 'adolescent', 'young adult', 'adult', 'senior adult',
        'senior'
    ]
    age_moons = {
        'newborn': game.config["cat_ages"]["newborn"],
        'kitten': game.config["cat_ages"]["kitten"],
        'adolescent': game.config["cat_ages"]["adolescent"],
        'young adult': game.config["cat_ages"]["young adult"],
        'adult': game.config["cat_ages"]["adult"],
        'senior adult': game.config["cat_ages"]["senior adult"],
        'senior': game.config["cat_ages"]["senior"]
    }

    all_cats: Dict[str, Cat] = {}  # ID: object
    outside_cats: Dict[str, Cat] = {}  # cats outside the clan
    id_iter = itertools.count()

    all_cats_list: List[Cat] = []
    ordered_cat_list: List[Cat] = []

    # This in is in reverse order: top of the list at the bottom
    

    rank_sort_order = [
        "newborn",
        "kitten",
        "queen's apprentice",
        "queen",
        "elder",
        "apprentice",
        "warrior",
        "mediator apprentice",
        "mediator",
        "medicine cat apprentice",
        "medicine cat",
        "deputy",
        "leader"
    ]

    gender_tags = {'molly': 'F', 'tom': 'M', 'intersex': 'I'}

    # EX levels and ranges.
    # Ranges are inclusive to both bounds
    experience_levels_range = {
        "untrained": (0, 0),
        "trainee": (1, 50),
        "prepared": (51, 110),
        "competent": (110, 170),
        "proficient": (171, 240),
        "expert": (241, 320),
        "master": (321, 321)
    }

    default_pronouns = [
        {
            "subject": "they",
            "object": "them",
            "poss": "their",
            "inposs": "theirs",
            "self": "themself",
            "conju": 1
        },
        {
            "subject": "she",
            "object": "her",
            "poss": "her",
            "inposs": "hers",
            "self": "herself",
            "conju": 2
        },
        {
            "subject": "he",
            "object": "him",
            "poss": "his",
            "inposs": "his",
            "self": "himself",
            "conju": 2
        }
    ]

    all_cats: Dict[str, Cat] = {}  # ID: object
    outside_cats: Dict[str, Cat] = {}  # cats outside the clan
    id_iter = itertools.count()

    all_cats_list: List[Cat] = []

    grief_strings = {}

    def __init__(self,
                 prefix=None,
                 gender=None,
                 status="newborn",
                 backstory="clanborn",
                 parent1=None,
                 parent2=None,
                 extrapar=None,
                 kittypet=False,
                 suffix=None,
                 specsuffix_hidden=False,
                 ID=None,
                 moons=None,
                 example=False,
                 faded=False,
                 skill_dict=None,
                 pelt:Pelt=None,
                 genotype:Genotype=None,
                 white_patterns=None,
                 chim_white=None,
                 loading_cat=False,  # Set to true if you are loading a cat at start-up.
                 **kwargs
                 ):

        # This must be at the top. It's a smaller list of things to init, which is only for faded cats
        self.history = None
        if faded:
            self.ID = ID
            self.name = Name(status, prefix=prefix, suffix=suffix)
            self.parent1 = None
            self.parent2 = None
            self.adoptive_parents = []
            self.mate = []
            self.status = status
            self.pronouns = [self.default_pronouns[0].copy()]
            self.moons = moons
            self.dead_for = 0
            self.shunned = 0
            self.dead = True
            self.outside = False
            self.exiled = False
            self.inheritance = None # This should never be used, but just for safety
            if "df" in kwargs:
                self.df = kwargs["df"]
            else:
                self.df = False
            if moons > 300:
                # Out of range, always elder
                self.age = 'senior'
            else:
                # In range
                for key_age in self.age_moons.keys():
                    if moons in range(self.age_moons[key_age][0], self.age_moons[key_age][1] + 1):
                        self.age = key_age

            self.set_faded()  # Sets the faded sprite and faded tag (self.faded = True)

            return
        
   

        self.generate_events = GenerateEvents()

        # Private attributes
        self._mentor = None  # plz
        self._experience = None
        self._moons = None

        # Public attributes
        self.gender = gender
        if self.gender == 'female':
            self.gender = 'fem'
        elif self.gender == 'male':
            self.gender = 'masc'
        self.status = status
        self.backstory = backstory
        self.age = None
        self.skills = CatSkills(skill_dict=skill_dict)
        self.personality = Personality(trait="troublesome", lawful=0, aggress=0,
                                       stable=0, social=0)
        self.parent1 = parent1
        self.parent2 = parent2
        
        self.adoptive_parents = []
        self.genotype = Genotype(game.config['genetic_chances'])
        if genotype:
            self.genotype.fromJSON(genotype)
        elif parent1 or parent2:
            if not parent1:
                self.genotype.KitGenerator(Cat.all_cats[parent2].genotype, extrapar)
            else:
                try:    
                    self.genotype.KitGenerator(Cat.all_cats[parent1].genotype, Cat.all_cats.get(parent2, extrapar))
                except:
                    self.genotype.Generator()

            if(randint(1, game.config['genetic_chances']['intersex']) == 1):
                self.genotype.gender = "intersex"
                if(randint(1, 25) == 1 and 'Y' in self.genotype.sexgene):
                    self.genotype.gender = 'molly'
        elif kittypet or status == 'kittypet':
            self.genotype.AltGenerator(special=self.gender)
            if(randint(1, game.config['genetic_chances']['intersex']) == 1):
                self.genotype.gender = "intersex"
                if(randint(1, 25) == 1 and 'Y' in self.genotype.sexgene):
                    self.genotype.gender = 'molly'
        else:
            self.genotype.Generator(special=self.gender)
            if(randint(1, game.config['genetic_chances']['intersex']) == 1):
                self.genotype.gender = "intersex"
                if(randint(1, 25) == 1 and 'Y' in self.genotype.sexgene):
                    self.genotype.gender = 'molly'

        self.phenotype = Phenotype(self.genotype)

        self.phenotype.PhenotypeOutput(self.genotype.gender)
        self.pelt = pelt if pelt else Pelt(self.genotype, self.phenotype)

        self.former_mentor = []
        self.patrol_with_mentor = 0
        self.apprentice = []
        self.former_apprentices = []
        self.relationships = {}
        self.mate = []
        self.previous_mates = []
        self.pronouns = [self.default_pronouns[0].copy()]
        self.placement = None
        self.example = example
        self.dead = False
        self.exiled = False
        self.outside = False
        self.dead_for = 0  # moons
        self.shunned = 0 # moons
        self.thought = ''
        self.genderalign = None
        self.birth_cooldown = 0
        self.illnesses = {}
        self.injuries = {}
        self.healed_condition = None
        self.leader_death_heal = None
        self.also_got = False
        self.permanent_condition = {}
        self.df = False
        self.experience_level = None
        
        white_pattern = white_patterns

        maingame_white = {
            'low':{
                '1': [None, 'SCOURGE', 'BLAZE', 'TAILTIP', 'TOES', 'LUNA', 'LOCKET'],
                '2': ['LITTLE', 'LIGHTTUXEDO', 'BUZZARDFANG', 'TIP', 'PAWS', 'BROKENBLAZE', 'BEARD', 'BIB', 'VEE', 'HONEY', 'TOESTAIL',
                      'RAVENPAW', 'DAPPLEPAW', 'LILTWO', 'MUSTACHE', 'REVERSEHEART', 'SPARKLE', 'REVERSEEYE'],
                '3': ['TUXEDO', 'SAVANNAH', 'FANCY', 'DIVA', 'BEARD', 'DAMIEN', 'BELLY', 'SQUEAKS', 'STAR', 'WINGS', 'MISS', 'BOWTIE',
                      'FCTWO', 'FCONE', 'MIA', 'PRINCESS', 'DOUGIE'],
                '4': ['TUXEDO', 'SAVANNAH', 'OWL', 'RINGTAIL', 'UNDERS', 'FAROFA', 'WINGS', 'VEST', 'FRONT', 'BLOSSOMSTEP', 'DIGIT',
                      'HAWKBLAZE'],
                '5': ['ANY', 'SHIBAINU', 'FAROFA', 'MISTER', 'PANTS', 'TRIXIE']
            },
            'high':{
                '1': ['ANY', 'SHIBAINU', 'PANTSTWO', 'MAO', 'TRIXIE'],
                '2': ['ANY', 'FRECKLES', 'PANTSTWO', 'MASKMANTLE', 'MAO', 'PAINTED', 'BUB', 'SCAR'],
                '3': ['ANYTWO', 'PEBBLESHINE', 'BROKEN', 'PIEBALD', 'FRECKLES', 'HALFFACE', 'GOATEE', 'PRINCE', 'CAPSADDLE', 
                      'REVERSEPANTS', 'GLASS', 'PAINTED', 'COWTWO', 'SAMMY', 'FINN', 'BUSTER', 'CAKE'],
                '4': ['VAN', 'PEBBLESHINE', 'LIGHTSONG', 'CURVED', 'GOATEE', 'TAIL', 'APRON', 'HALFWHITE', 'APPALOOSA', 'HEART',
                      'MOORISH', 'COW', 'SHOOTINGSTAR', 'PEBBLE', 'TAILTWO', 'BUDDY', 'KROPKA'],
                '5': ['ONEEAR', 'LIGHTSONG', 'BLACKSTAR', 'PETAL', 'CHESTSPECK', 'HEARTTWO', 'BOOTS', 'SHOOTINGSTAR', 'EYESPOT', 
                      'KROPKA']
            }
        }

        vitiligo = ['MOON', 'PHANTOM', 'POWDER', 'BLEACHED', 'VITILIGO', 'VITILIGOTWO', 'SMOKEY']

        #white patterns
        
        def GenerateWhite(KIT, KITgrade, vit, white_pattern):
            def clean_white():
                while None in white_pattern:
                    white_pattern.remove(None)

            if white_pattern is None and (KIT[0] != "W" and KIT[0] != "w"):
                white_pattern = []
                if(vit):
                    white_pattern.append(choice(vitiligo))
                if KIT[0] == 'wt' or KIT[1] == 'wt':
                    if KIT[1] not in ['ws', 'wt'] and KITgrade < 3:
                        white_pattern.append("dorsal1")
                    elif KIT[1] not in ['ws', 'wt'] and KITgrade < 5:
                        white_pattern.append(choice(["dorsal1", "dorsal2"]))
                    else:
                        white_pattern.append("dorsal2")
                
                if KIT[0] == "wg":
                    for mark in ["left front mitten", "left back mitten", "right front mitten", "right back mitten"]:
                        white_pattern.append(mark)
                elif KIT[0] in ["ws", "wt"] and KIT[1] not in ["ws", "wt"]:
                    
                    if(randint(1, 4) == 1):
                        white_pattern.append(choice(maingame_white["low"].get(str(KITgrade))))
                        clean_white()

                    elif KITgrade == 1:
                        grade1list = ['chest tuft', 'belly tuft', 'chest tuft', 'belly tuft', None]
                        white_pattern.append(choice(grade1list))
                        clean_white()
                    elif KITgrade == 2:
                        while len(white_pattern) == 0:
                            #chest
                            white_pattern.append(choice(['chest tuft', 'locket', None, 'chest tuft', 'locket', None, 'bib']))
                            #belly
                            white_pattern.append(choice(['belly tuft', 'belly spot', None, 'belly tuft', 'belly spot', None, 'belly']))

                            #toes
                            nropaws = choice([4, 3, 2, 1, 0, 0])
                            order = ['right front', 'left front', 'right back', 'left back']
                            shuffle(order)

                            for i in range(nropaws):
                                white_pattern.append(order[i] + choice([' toes', ' toes', ' toes', ' mitten']))
                        clean_white()
                    elif KITgrade == 3:
                        while len(white_pattern) < 4:
                            #chest
                            white_pattern.append(choice(['chest', 'beard', 'chest', 'bib', None]))

                            #belly
                            white_pattern.append(choice(['belly spot', 'belly', 'belly spot', 'belly', 'belly spot', 'belly', None]))

                            #paws
                            nropaws = choice([4, 4, 3, 2, 1, 0])
                            order = ['right front', 'left front', 'right back', 'left back']
                            shuffle(order)
                            pawtype = choice(['same', 'mixed'])

                            for i in range(nropaws):
                                if pawtype == 'same':
                                    pawtype = choice([' toes', ' mitten', ' mitten', ' mitten', ' low sock'])
                                    white_pattern.append(order[i] + pawtype)
                                else:
                                    white_pattern.append(order[i] + choice([' toes', ' mitten', ' mitten', ' low sock']))

                            #face
                            if 'beard' in white_pattern:
                                white_pattern.append(choice(['chin', 'mustache', 'chin', 'chin', None, None, None, None]))

                            #tail
                            white_pattern.append(choice(['tail tip', None, None, None, None]))
                            white_pattern.append(choice([None, None, None, 'break/nose1']))

                            clean_white()
                    elif KITgrade == 4:
                        while len(white_pattern) < 4:
                            #chest
                            white_pattern.append(choice(['underbelly1', 'beard', 'chest', 'underbelly1']))

                            #belly
                            if 'underbelly1' not in white_pattern:
                                white_pattern.append('belly')

                            #paws
                            nropaws = choice([4, 4, 4, 4, 3, 3, 2, 2, 1, 0])
                            order = ['right front', 'left front', 'right back', 'left back']
                            shuffle(order)
                            pawtype = choice(['same', 'mixed'])

                            for i in range(nropaws):
                                if pawtype == 'same':
                                    pawtype = choice([' mitten', ' low sock', ' low sock', ' high sock'])
                                    white_pattern.append(order[i] + pawtype)
                                else:
                                    white_pattern.append(order[i] + choice([' mitten', ' low sock', ' high sock']))

                            #face
                            if 'beard' or 'underbelly1' in white_pattern:
                                white_pattern.append(choice(['chin', 'chin', 'muzzle', 'muzzle', 'blaze', None, None]))

                            #tail
                            white_pattern.append(choice(['tail tip', None, None, None, None]))
                            white_pattern.append(choice([None, None, None, 'break/nose1']))

                            clean_white()
                    else:
                        while len(white_pattern) < 4:
                            #chest
                            white_pattern.append('underbelly1')

                            #paws
                            nropaws = 4
                            order = ['right front', 'left front', 'right back', 'left back']
                            shuffle(order)
                            pawtype = choice(['same', 'mixed'])

                            for i in range(nropaws):
                                if pawtype == 'same':
                                    pawtype = choice([' high sock', ' bicolour1', ' bicolour1', ' bicolour2'])
                                    white_pattern.append(order[i] + pawtype)
                                else:
                                    white_pattern.append(order[i] + choice([' high sock', ' bicolour1', ' bicolour1', ' bicolour2']))

                            #face
                            white_pattern.append(choice(['chin', 'muzzle', 'muzzle', 'muzzle', 'blaze']))

                            #tail
                            white_pattern.append(choice(['tail tip', None, None, None, None]))
                            white_pattern.append(choice([None, None, None, 'break/nose1']))

                            clean_white()
                else:
                    
                    if(randint(1, 4) == 1):
                        white_pattern.append(choice(maingame_white["high"].get(str(KITgrade))))

                    elif KITgrade == 1:
                        while len(white_pattern) < 4:
                            #chest
                            white_pattern.append('underbelly1')

                            #paws
                            nropaws = 4
                            order = ['right front', 'left front', 'right back', 'left back']
                            shuffle(order)
                            pawtype = choice(['same', 'mixed'])

                            for i in range(nropaws):
                                if pawtype == 'same':
                                    pawtype = choice([' bicolour1', ' bicolour2', ' bicolour2'])
                                    white_pattern.append(order[i] + pawtype)
                                else:
                                    white_pattern.append(order[i] + choice([' bicolour1', ' bicolour2', ' bicolour2']))

                            #face
                            white_pattern.append(choice(['chin', 'muzzle', 'muzzle', 'muzzle', 'blaze', 'blaze']))

                            #tail
                            white_pattern.append(choice(['tail tip', None, None, None, None]))
                            white_pattern.append(choice([None, None, None, 'break/nose1']))

                            clean_white()
                    elif KITgrade == 2:
                        #chest
                        white_pattern.append(choice(['underbelly1', 'mask n mantle']))

                        #paws
                        nropaws = 4
                        order = ['right front', 'left front', 'right back', 'left back']
                        shuffle(order)
                        pawtype = choice(['same', 'mixed'])

                        for i in range(nropaws):
                            white_pattern.append(order[i] + ' bicolour2')

                        #face
                        white_pattern.append(choice(['muzzle', 'muzzle', 'blaze', 'blaze']))

                        #tail
                        white_pattern.append(choice(['tail tip', None, None, None, None]))
                        white_pattern.append(choice([None, None, None, 'break/nose1']))
                        clean_white()
                    elif KITgrade == 3:
                        white_pattern.append(choice(['van1', 'van2', 'van3', 'van1', 'van2', 'van3', 'full white']))
                        white_pattern.append(choice(['break/piebald1', 'break/piebald2']))
                        white_pattern.append(choice([None, 'break/left ear', 'break/right ear', 'break/tail tip', 'break/tail band', 'break/tail rings', 'break/left face', 'break/right face']))
                        clean_white()
                    elif KITgrade == 4:
                        white_pattern.append(choice(['van1', 'van2', 'van3']))
                        white_pattern.append(choice([None, None, choice(['break/left ear', 'break/right ear', 'break/tail tip', 'break/tail band', 'break/left face', 'break/right face'])]))
                        white_pattern.append(choice([None, None, None, None, None, choice(['break/left ear', 'break/right ear', 'break/tail tip', 'break/tail band', 'break/left face', 'break/right face'])]))

                        clean_white()
                    else:
                        white_pattern.append(choice(["full white", 'van3']))

                        white_pattern.append(choice([None, 'break/left ear', 'break/right ear', 'break/tail tip', 'break/tail band', 'break/left face', 'break/right face']))
                        white_pattern.append(choice([None, choice(['break/left ear', 'break/right ear', 'break/tail tip', 'break/tail band', 'break/left face', 'break/right face'])]))

                        clean_white()
                
            elif white_pattern is None and vit:
                white_pattern = [choice(vitiligo)]
            if white_pattern == [] or white_pattern is None:
                white_pattern = "No"
            return white_pattern

        self.genotype.white_pattern = GenerateWhite(self.genotype.white, self.genotype.whitegrade, self.genotype.vitiligo, white_pattern)

        white_pattern = chim_white
        if self.genotype.chimera:    
            self.genotype.chimerageno.white_pattern = GenerateWhite(self.genotype.chimerageno.white, self.genotype.chimerageno.whitegrade, self.genotype.chimerageno.vitiligo, white_pattern)
        
        #elif white_pattern == "No":
        #    white_pattern = None
        
        self.no_kits = False
        self.w_done = False
        self.talked_to = False
        self.insulted = False
        self.flirted = False
        self.joined_df = False
        self.forgiven = 0
        self.inventory = []
        self.revives = 0
        self.no_kits = False
        self.no_mates = False
        self.no_retire = False
        self.backstory_str = ""
        self.courage = 0
        self.compassion = 0
        self.intelligence = 0
        self.empathy = 0
        self.did_activity = False
        self.df_mentor = None
        self.df_apprentices = []
        
        self.prevent_fading = False  # Prevents a cat from fading.
        self.faded_offspring = []  # Stores of a list of faded offspring, for family page purposes.

        self.faded = faded  # This is only used to flag cat that are faded, but won't be added to the faded list until
        # the next save.
    
        if (self.genotype.munch[1] == "Mk" or self.genotype.fold[1] == "Fd" or (self.genotype.manx[1] == "Ab" or self.genotype.manx[1] == "M")):
            self.dead = True

        self.favourite = False

        self.specsuffix_hidden = specsuffix_hidden
        self.inheritance = None

        self.history = None

        # setting ID
        if ID is None:
            potential_id = str(next(Cat.id_iter))

            if game.clan:
                faded_cats = game.clan.faded_ids
            else:
                faded_cats = []

            while potential_id in self.all_cats or potential_id in faded_cats:
                potential_id = str(next(Cat.id_iter))
            self.ID = potential_id
        else:
            self.ID = ID

        # age and status
        if status is None and moons is None:
            self.age = choice(self.ages)
        elif moons is not None:
            self.moons = moons
            if moons > 300:
                # Out of range, always elder
                self.age = 'senior'
            elif moons == 0 or moons == -1:
                self.age = 'newborn'
            else:
                # In range
                for key_age in self.age_moons.keys():
                    if moons in range(self.age_moons[key_age][0], self.age_moons[key_age][1] + 1):
                        self.age = key_age
        else:
            if status == 'newborn':
                self.age = 'newborn'
            elif status == 'kitten':
                self.age = 'kitten'
            elif status == 'elder':
                self.age = 'senior'
            elif status in ['apprentice', 'mediator apprentice', 'medicine cat apprentice', "queen's apprentice"]:
                self.age = 'adolescent'
            else:
                self.age = choice(['young adult', 'adult', 'adult', 'senior adult'])
            self.moons = randint(self.age_moons[self.age][0], self.age_moons[self.age][1])
       

        if self.genotype.deaf:
            if 'blue' not in self.genotype.lefteyetype or 'blue' not in self.genotype.righteyetype:
                self.get_permanent_condition('partial hearing loss', born_with=True)
            elif 'partial hearing loss' not in self.permanent_condition:
                self.get_permanent_condition(choice(['deaf', 'partial hearing loss']), born_with=True)
        
        if self.genotype.manx[0] == 'M' and (self.genotype.manxtype in ['rumpy', 'riser']):
            self.get_permanent_condition('born without a tail', born_with=True)
        
        if len(self.genotype.sexgene) > 2 and 'Y' in self.genotype.sexgene or (not loading_cat and self.gender == 'intersex' and random() < 0.2 and not gender) or (self.gender == 'molly' and 'Y' in self.genotype.sexgene):
            self.get_permanent_condition('infertility', born_with=True)
        
        if self.genotype.fold[0] == 'Fd':
            self.get_permanent_condition('constant joint pain', born_with=True)

        # backstory
        if self.backstory is None:
            self.backstory = 'clanborn'
        else:
            self.backstory = self.backstory
        


        # sex!?!??!?!?!??!?!?!?!??
        
        self.gender = self.genotype.gender
        self.g_tag = self.gender_tags[self.gender]


        # These things should only run when generating a new cat, rather than loading one in.
        if not loading_cat:
            # trans cat chances
            trans_chance = randint(0, 50)
            nb_chance = randint(0, 75)
            self.genderalign = ""
            if(self.gender == 'intersex'):
                self.genderalign = 'intersex '
            if (self.gender == "molly" or (self.gender == 'intersex' and 'Y' not in self.genotype.sexgene)) and not self.status in ['newborn', 'kitten']:
                if trans_chance == 1:
                    self.genderalign = "trans tom"
                elif nb_chance == 1:
                    self.genderalign = "sam"
                else:
                    if(self.gender == 'intersex'):
                        if('Y' in self.genotype.sexgene):
                            self.genderalign += 'tom'
                        else:
                            self.genderalign += 'molly'
                    else:
                        self.genderalign += self.gender
            elif (self.gender == "tom" or (self.gender == 'intersex' and 'Y' in self.genotype.sexgene)) and not self.status in ['newborn', 'kitten']:
                if trans_chance == 1:
                    self.genderalign = "trans molly"
                elif nb_chance == 1:
                    self.genderalign = "sam"
                else:
                    if(self.gender == 'intersex'):
                        if('Y' in self.genotype.sexgene):
                            self.genderalign += 'tom'
                        else:
                            self.genderalign += 'molly'
                    else:
                        self.genderalign += self.gender
            else:
                if(self.gender == 'intersex'):
                    if('Y' in self.genotype.sexgene):
                        self.genderalign += 'tom'
                    else:
                        self.genderalign += 'molly'
                else:
                    self.genderalign += self.gender

            # """if self.genderalign in ["molly", "trans molly"]:
            #     self.pronouns = [self.default_pronouns[1].copy()]
            # elif self.genderalign in ["tom", "trans tom"]:
            #     self.pronouns = [self.default_pronouns[2].copy()]"""

            # APPEARANCE
            self.pelt = Pelt.generate_new_pelt(self.genotype, self.phenotype, self.gender, [Cat.fetch_cat(i) for i in (self.parent1, self.parent2) if i], self.age)
            
            #Personality
            self.personality = Personality(kit_trait=self.is_baby())

            # experience and current patrol status
            if self.age in ['young', 'newborn']:
                self.experience = 0
            elif self.age in ['adolescent']:
                m = self.moons
                self.experience = 0
                while m > Cat.age_moons['adolescent'][0]:
                    ran = game.config["graduation"]["base_app_timeskip_ex"]
                    exp = choice(
                        list(range(ran[0][0], ran[0][1] + 1)) + list(range(ran[1][0], ran[1][1] + 1)))
                    self.experience += exp + 3
                    m -= 1
            elif self.age in ['young adult', 'adult']:
                self.experience = randint(Cat.experience_levels_range["prepared"][0],
                                          Cat.experience_levels_range["proficient"][1])
            elif self.age in ['senior adult']:
                self.experience = randint(Cat.experience_levels_range["competent"][0],
                                          Cat.experience_levels_range["expert"][1])
            elif self.age in ['senior']:
                self.experience = randint(Cat.experience_levels_range["competent"][0],
                                          Cat.experience_levels_range["master"][1])
            else:
                self.experience = 0
                
            if not skill_dict:
                self.skills = CatSkills.generate_new_catskills(self.status, self.moons)

        # In camp status
        self.in_camp = 1
        if "biome" in kwargs:
            biome = kwargs["biome"]
        elif game.clan is not None:
            biome = game.clan.biome
        else:
            biome = None
        # NAME
        # load_existing_name is needed so existing cats don't get their names changed/fixed for no reason
        if self.pelt is not None:
            self.name = Name(status,
                             prefix,
                             suffix,
                             self.pelt.colour,
                             self.pelt.eye_colour,
                             self.pelt.name,
                             self.pelt.tortiepattern,
                             biome=biome,
                             specsuffix_hidden=self.specsuffix_hidden,
                             load_existing_name=loading_cat)
        else:
            self.name = Name(status, prefix, suffix, eyes=self.pelt.eye_colour, specsuffix_hidden=self.specsuffix_hidden,
                             load_existing_name = loading_cat)

        # Private Sprite
        self._sprite = None

        # SAVE CAT INTO ALL_CATS DICTIONARY IN CATS-CLASS
        self.all_cats[self.ID] = self

        if self.ID not in ["0", None]:
            Cat.insert_cat(self)

    def __repr__(self):

        
        return "CAT OBJECT:" + self.ID
            
    @property
    def mentor(self):
        """Return managed attribute '_mentor', which is the ID of the cat's mentor."""
        return self._mentor

    @mentor.setter
    def mentor(self, mentor_id: Any):
        """Makes sure Cat.mentor can only be None (no mentor) or a string (mentor ID)."""
        if mentor_id is None or isinstance(mentor_id, str):
            self._mentor = mentor_id
        else:
            print(f"Mentor ID {mentor_id} of type {type(mentor_id)} isn't valid :("
                  "\nCat.mentor has to be either None (no mentor) or the mentor's ID as a string.")

    def is_alive(self):
        return not self.dead

    def die(self, body: bool = True):
        """
        This is used to kill a cat.

        body - defaults to True, use this to mark if the body was recovered so
        that grief messages will align with body status 
        - if it is None, a lost cat died and therefore not trigger grief, since the clan does not know

        May return some additional text to add to the death event.
        """
        if self.status == 'leader' and 'pregnant' in self.injuries and game.clan.leader_lives > 0:
            self.illnesses.clear()
            self.injuries = { key : value for (key, value) in self.injuries.items() if key == 'pregnant'}
        else:
            self.injuries.clear()
            self.illnesses.clear()
        
        # Deal with leader death
        text = ""
        if self.status == 'leader':
            if game.clan.leader_lives > 0:
                self.thought = 'Was startled to find themselves in Silverpelt for a moment... did they lose a life?'
                return ""
            elif game.clan.leader_lives <= 0:
                self.dead = True
                game.just_died.append(self.ID)
                game.clan.leader_lives = 0
                self.thought = 'Is surprised to find themselves walking the stars of Silverpelt'
                if game.clan.followingsc is True:
                    text = 'They\'ve lost their last life and have travelled to StarClan.'
                else:
                    text = 'They\'ve lost their last life and have travelled to the Dark Forest.'
        else:
            self.dead = True
            game.just_died.append(self.ID)
            self.thought = 'Is surprised to find themselves walking the stars of Silverpelt'

        # Clear Relationships. 
        if self.ID != game.clan.your_cat.ID:
            self.relationships = {}

        for app in self.apprentice.copy():
            fetched_cat = Cat.fetch_cat(app)
            if fetched_cat:
                fetched_cat.update_mentor()
        self.update_mentor()

        if game.clan and game.clan.game_mode != 'classic' and not (self.outside or self.exiled) and body is not None:
            self.grief(body)

        if not self.outside:
            if self.status not in ["loner", "kittypet", "rogue", "former Clancat"]:
                #^^ seems redundant but fixes a bug where, if following the DF before the mc
                # is born, and mc is not clanborn, their birth parent will be in both the DF and UR
                Cat.dead_cats.append(self)
                if game.clan.followingsc is False:
                    self.df = True
                    self.thought = "Is startled to find themselves wading in the muck of a shadowed forest"
                    game.clan.add_to_darkforest(self)
                else:
                    self.thought = 'Is surprised to find themselves walking the stars of Silverpelt'
                    
                if self.history:
                    if self.history.murder:
                        if "is_murderer" in self.history.murder:
                            if len(self.history.murder["is_murderer"]) > 2:
                                self.df = True
                                self.thought = "Is startled to find themselves wading in the muck of a shadowed forest"
                                game.clan.add_to_darkforest(self)

                if self.shunned > 0 and self.forgiven > 1:
                    self.df = True
                    self.thought = "Is startled to find themselves wading in the muck of a shadowed forest"
                    game.clan.add_to_darkforest(self)
                elif self.shunned == 0 and self.forgiven > 0:
                    self.thought = "Is shocked they made it into StarClan"
                    game.clan.add_to_starclan(self)
            
        else:
            self.thought = "Is fascinated by the new ghostly world they've stumbled into"
            game.clan.add_to_unknown(self)
        
        if self.shunned > 0:
            self.shunned = 0

        if self.exiled:
            self.status = 'former Clancat'

        return text

    def exile(self):
        """This is used to send a cat into exile. This removes the cat's status and gives them a special 'exiled'
        status."""
        self.exiled = True
        self.outside = True
        self.status = 'exiled'
        if self.personality.trait == 'vengeful':
            self.thought = "Swears their revenge for being exiled"
        else:
            self.thought = "Is shocked that they have been exiled"
        for app in self.apprentice:
            fetched_cat = Cat.fetch_cat(app)
            if fetched_cat:
                fetched_cat.update_mentor()
        self.update_mentor()

# pylint: disable=f-string-without-interpolation
    def handle_exile_returns(self):
        """outside cats returnin"""
       
            
        exiled_cats = [cat for cat in Cat.all_cats.values() if cat.exiled and not cat.dead]
        
        if len(exiled_cats) > 20:
            run = randint(1,80)
        elif len(exiled_cats) > 10:
            run = randint(1,60)
        elif len(exiled_cats) > 5:
            run = randint(1,40)
        else:
            run = randint(1,20)
        
        if run == 2:

            exiled_cat = choice(exiled_cats)

            event_text = f"The entire Clan is shocked when {exiled_cat.name} shows up at the camp entrance. They asked to be let back into the Clan, "

            allowchance = randint(1,3)
            if allowchance == 1:
                event_text = event_text + f"and, after a Clan meeting is held, it's decided that they will be allowed back in."
                exiled_cat.exiled = False
                Cat.add_to_clan(exiled_cat)
                if exiled_cat.moons > 119:
                    exiled_cat.status = "elder"
                elif exiled_cat.moons > 12:
                    exiled_cat.status = "warrior"
                elif exiled_cat.moons > 6:
                    exiled_cat.status = "apprentice"
                else:
                    exiled_cat.status = "kitten"
            else:
                event_text = event_text + f"but the more vengeful of {game.clan.name}Clan's members chase them out and leave them with a few scars to remember their past home by."

                scar = choice(["ONE", "TWO", "THREE", "TAILSCAR", "SNOUT", "CHEEK", "SIDE", "THROAT", "TAILBASE", "BELLY",
                "LEGBITE", "NECKBITE", "FACE", "MANLEG", "MANTAIL", "BRIDGE", "RIGHTBLIND", "LEFTBLIND",
                "BOTHBLIND", "CATBITE", "HINDLEG", "BACK", "SCRATCHSIDE", "CATBITETWO", "FOUR"])

                exiled_cat.pelt.scars.append(scar if scar not in exiled_cat.pelt.scars and len(exiled_cat.pelt.scars) < 4 else None)

            involved_cats = [exiled_cat.ID]
            game.cur_events_list.append(Single_Event(event_text, ["misc"], involved_cats))

    def return_home(self):
        """
        Handles the outside MC attempting to return to the Clan
        """

        you = game.clan.your_cat
        if not you.outside:
            return
        
        murder_history = History.get_murders(you)
        num_victims = 0
        if murder_history:
            if 'is_murderer' in murder_history:
                num_victims = len(murder_history["is_murderer"])

        nice = you.personality.trait in ["charismatic", "confident", "flexible", "witty", "loyal", "responsible", "faithful", "compassionate", "sincere", "sweet", "polite"]
        naughty = you.personality.trait in ["bloodthirsty", "sneaky", "manipulative", "strange", "rebellious", "troublesome", "stoic", "aloof", "cunning"]
        acceptchance = randint(1,5)
        killchance = randint(1,50)
        if you.exiled:

            if num_victims == 0:
                acceptchance = randint (1,4)
                killchance = randint(1,40)
            
            elif num_victims == 1: # one victim
                if nice:
                    acceptchance = randint (1,5)
                    killchance = randint(1,40)
                elif naughty:
                    acceptchance = randint(1,10)
                    killchance = randint(1,30)
                else:
                    acceptchance = randint(1,8)
                    killchance = randint(1,30)

            elif num_victims < 4: # 2-3 victims
                if nice:
                    acceptchance = randint (1,10)
                    killchance = randint(1,35)
                elif naughty:
                    acceptchance = randint(1,20)
                    killchance = randint(1,22)
                else:
                    acceptchance = randint(1,15)
                    killchance = randint(1,30)

            elif num_victims < 7: # 4-6 victims
                if nice:
                    acceptchance = randint (1,15)
                    killchance = randint(1,30)
                elif naughty:
                    acceptchance = randint(1,30)
                    killchance = randint(1,15)
                else:
                    acceptchance = randint(1,30)
                    killchance = randint(1,30)

            elif num_victims < 10: # 7-9 victims
                if nice:
                    acceptchance = randint (1,25)
                    killchance = randint(1,20)
                elif naughty:
                    acceptchance = randint(1,35)
                    killchance = randint(1,10)
                else:
                    acceptchance = randint(1,30)
                    killchance = randint(1,12)
            else: # 10+ victims?????!!?!
                if nice:
                    acceptchance = randint (1,35)
                    killchance = randint(1,15)
                elif naughty:
                    acceptchance = randint(1,45)
                    killchance = randint(1,8)
                else:
                    acceptchance = randint(1,40)
                    killchance = randint(1,10)

        elif you.status in ["loner", "rogue", "kittypet", "former Clancat"]:
        # can only be former clancat rn but this is just to cover bases 4 the future
            if num_victims == 0:
                acceptchance = randint(1,3)
                killchance = randint(1,50)
            
            elif num_victims == 1: # one victim
                if nice:
                    acceptchance = randint (1,4)
                    killchance = randint(1,40)
                elif naughty:
                    acceptchance = randint(1,8)
                    killchance = randint(1,30)
                else:
                    acceptchance = randint(1,6)
                    killchance = randint(1,30)

            elif num_victims < 4: # 2-3 victims
                if nice:
                    acceptchance = randint (1,8)
                    killchance = randint(1,35)
                elif naughty:
                    acceptchance = randint(1,15)
                    killchance = randint(1,22)
                else:
                    acceptchance = randint(1,10)
                    killchance = randint(1,30)

            elif num_victims < 7: # 4-6 victims
                if nice:
                    acceptchance = randint (1,10)
                    killchance = randint(1,30)
                elif naughty:
                    acceptchance = randint(1,25)
                    killchance = randint(1,15)
                else:
                    acceptchance = randint(1,20)
                    killchance = randint(1,30)

            elif num_victims < 10: # 7-9 victims
                if nice:
                    acceptchance = randint (1,20)
                    killchance = randint(1,20)
                elif naughty:
                    acceptchance = randint(1,30)
                    killchance = randint(1,10)
                else:
                    acceptchance = randint(1,20)
                    killchance = randint(1,12)
            else: # 10+ victims?????!!?!
                if nice:
                    acceptchance = randint (1,35)
                    killchance = randint(1,15)
                elif naughty:
                    acceptchance = randint(1,35)
                    killchance = randint(1,8)
                else:
                    acceptchance = randint(1,30)
                    killchance = randint(1,10)

        if you.exiled:
            event_text = f"You muster up your courage and turn to walk back home, hoping that your Clanmates will be able to forgive you. At the {game.clan.name}Clan border, you sit and wait for a patrol. <br>"

        elif you.outside:
            event_text = f"You're ready to return home-- you're sure of it. You hope that your Clanmates will take you back in as you head for the {game.clan.name}Clan border to wait for a patrol. <br> "
        if acceptchance == 1:
            event_text = event_text + f"When one finally comes, they're wary, but they agree to take you back to camp, and a Clan meeting is held. After much deliberation, it's decided that you will be allowed back home."
            you.exiled = False
            if you.moons > 119:
                you.status_change("elder")
            elif you.moons > 12:
                you.status_change("warrior")
            elif you.moons > 6:
                you.status_change("apprentice")
            else:
                you.status_change("kitten")
            you.thought = "Is happy to be home!"

            if you.exiled:
                you.exiled = False
                
            Cat.add_to_clan(you)

        elif killchance == 1:
            event_text = event_text + f"The patrol immediately meets you with hostility, and when you ask to visit camp, the more vengeful among the group instantly attack you, spitting at you that you don't deserve to step foot on {game.clan.name}Clan's territory after what you did. As your vision begins to blur, the last thing you hear is a former Clanmate damning you to the Dark Forest."
            Cat.die(you)
            if you.moons > 119:
                you.status_change("elder")
            elif you.moons > 12:
                you.status_change("warrior")
            elif you.moons > 6:
                you.status_change("apprentice")
            else:
                you.status_change("kitten")
            if you.exiled:
                you.exiled = False
        elif killchance in [2, 3, 4, 5, 6]:
            event_text = event_text + choice ([ f"The patrol responds to your greeting with hisses and growls. Before you can even ask to head back to camp with them, a set of claws shoots towards you and you're met with the view of your blood hitting the grass. You don't have to be told twice-- you retreat back to your makeshift home.",
            f"As soon as a patrol catches your eye, they erupt into hisses and yowls. You scramble to your paws, but you don't get away in time to avoid a fresh wound from an angry ex-clanmate. They scream after you that there will never be a place for you in {game.clan.name}Clan again."])

            scar = choice(["ONE", "TWO", "THREE", "TAILSCAR", "SNOUT", "CHEEK", "SIDE", "THROAT", "TAILBASE", "BELLY",
            "LEGBITE", "NECKBITE", "FACE", "MANLEG", "MANTAIL", "BRIDGE", "RIGHTBLIND", "LEFTBLIND",
            "BOTHBLIND", "CATBITE", "HINDLEG", "BACK", "SCRATCHSIDE", "CATBITETWO", "FOUR"])

            you.pelt.scars.append(scar if scar not in you.pelt.scars and len(you.pelt.scars) < 4 else None)
            you.thought = "Licks their wounds"
        else:
            event_text = event_text + choice([ f"When one finally comes along, they meet you with wary eyes. A few of the more forthcoming members of the group share some Clan news, but when they turn to head back to camp, you're not invited, and the leader of the patrol lingers nearby until you turn to leave.",
            f"Eventually, one finds you, but they aren't as happy to see you as you'd have liked. You share some pleasantries with a couple of kind patrol members, but the others stay silent and on edge. After a short talk, they turn to leave, making it clear that you're not to come with them.",
            f"You wait for a long time. Eventually, you see the flicker of a bright pelt through the trees, but they quickly turn away, and as the sun starts to set, you reluctantly leave to find somewhere to sleep."])

            you.thought = "Wants to try again"
        game.cur_events_list.insert(0, Single_Event(event_text))

    
    def grief(self, body: bool):
        """
        compiles grief moon event text
        """
        if body is True:
            body_status = 'body'
        else:
            body_status = 'no_body'
    
        # Keep track is the body was treated with rosemary. 
        body_treated = False
    
        # apply grief to cats with high positive relationships to dead cat
        for cat in Cat.all_cats.values():
            if cat.dead or cat.outside or cat.moons < 1:
                continue
            
            to_self = cat.relationships.get(self.ID)
            if not isinstance(to_self, Relationship):
                continue
            
            family_relation = self.familial_grief(living_cat=cat)
            very_high_values = []
            high_values = []
            
            if to_self.romantic_love > 55:
                very_high_values.append("romantic")
            if to_self.romantic_love > 40:
                high_values.append("romantic")
            
            if to_self.platonic_like > 50:
                very_high_values.append("platonic")
            if to_self.platonic_like > 30:
                high_values.append("platonic")
            
            if to_self.admiration > 70:
                very_high_values.append("admiration")
            if to_self.admiration > 50:
                high_values.append("admiration")
                
            if to_self.comfortable > 60:
                very_high_values.append("comfort")
            if to_self.comfortable > 40:
                high_values.append("comfort")
                
            if to_self.trust > 70:
                very_high_values.append("trust")
            if to_self.trust > 50:
                high_values.append("trust")
            
            
            major_chance = 0
            if very_high_values:
                # major grief eligible cats. 
                
                major_chance = 3
                if cat.personality.stability < 5:
                    major_chance -= 1
                
                # decrease major grief chance if grave herbs are used
                if not body_treated and "rosemary" in game.clan.herbs:  
                    body_treated = True
                    game.clan.herbs["rosemary"] -= 1
                    if game.clan.herbs["rosemary"] <= 0:
                        game.clan.herbs.pop("rosemary")
                    game.herb_events_list.append(f"Rosemary was used for {self.name}'s body.")
                
                if body_treated:
                    major_chance -= 1
                
            
            # If major_chance is not 0, there is a chance for major grief
            grief_type = None
            if major_chance and not int(random() * major_chance):
                
                grief_type = "major"
                
                possible_strings = []
                for x in very_high_values:
                    possible_strings.extend(
                        self.generate_events.possible_death_reactions(family_relation, x, cat.personality.trait,
                                                                body_status)
                    )
                
                if not possible_strings:
                    print("No grief strings")
                    continue
                
                text = choice(possible_strings)
                text += ' ' + choice(MINOR_MAJOR_REACTION["major"])
                text = event_text_adjust(Cat, text, self, cat)
                
                # grief the cat
                if game.clan.game_mode != 'classic':
                    cat.get_ill("grief stricken", event_triggered=True, severity="major", grief_cat = self)
            
            # If major grief fails, but there are still very_high or high values, 
            # it can fail to to minor grief. If they have a family relation, bypass the roll. 
            elif (very_high_values or high_values) and \
                    (family_relation != "general" or not int(random() * 5)):
            
                grief_type = "minor"
                
                # These minor grief message will be applied as thoughts. 
                minor_grief_messages = (
                            "Told a fond story at r_c's vigil",
                            "Bargains with StarClan, begging them to send r_c back",
                            "Sat all night at r_c's vigil",
                            "Will never forget r_c",
                            "Prays that r_c is safe in StarClan",
                            "Misses the warmth that r_c brought to {PRONOUN/m_c/poss} life",
                            "Is mourning r_c"
                        )
                
                if body: 
                    minor_grief_messages += (
                        "Helped bury r_c, leaving {PRONOUN/r_c/poss} favorite prey at the grave",
                        "Slips out of camp to visit r_c's grave"
                    )

                
                text = choice(minor_grief_messages)
                
            if grief_type:
                #Generate the event:
                if cat.ID not in Cat.grief_strings:
                    Cat.grief_strings[cat.ID] = []
                
                Cat.grief_strings[cat.ID].append((text, (self.ID, cat.ID), grief_type))
                continue
            
            
            # Negative "grief" messages are just for flavor. 
            high_values = []
            very_high_values = []
            if to_self.dislike > 50:
                high_values.append("dislike")
                
            if to_self.jealousy > 50:
                high_values.append("jealousy")
            
            if high_values:
                #Generate the event:
                possible_strings = []
                for x in high_values:
                    possible_strings.extend(
                        self.generate_events.possible_death_reactions(family_relation, x, cat.personality.trait,
                                                                body_status)
                    )
                
                text = event_text_adjust(Cat, choice(possible_strings), self, cat)
                if cat.ID not in Cat.grief_strings:
                    Cat.grief_strings[cat.ID] = []
                
                Cat.grief_strings[cat.ID].append((text, (self.ID, cat.ID), "negative"))
                

    def familial_grief(self, living_cat: Cat):
        """
        returns relevant grief strings for family members, if no relevant strings then returns None
        """
        dead_cat = self

        if dead_cat.is_parent(living_cat):
            return "child"
        elif living_cat.is_parent(dead_cat):
            return "parent"
        elif dead_cat.is_sibling(living_cat):
            return "sibling"
        else:
            return "general"

    def gone(self):
        """ Makes a Clan cat an "outside" cat. Handles removing them from special positions, and removing
        mentors and apprentices. """
        self.outside = True
        
        if self.status in ['leader', 'warrior']:
            self.status_change("warrior")

        for app in self.apprentice.copy():
            app_ob = Cat.fetch_cat(app)
            if app_ob:
                app_ob.update_mentor()
        self.update_mentor()
        for x in self.apprentice:
            Cat.fetch_cat(x).update_mentor()
        game.clan.add_to_outside(self)

    def add_to_clan(self) -> list:
        """ Makes a "outside cat" a Clan cat. Returns a list of any additional cats that
            are coming with them. """
        self.outside = False

        game.clan.add_to_clan(self)

        # check if there are kits under 12 moons with this cat and also add them to the clan
        children = self.get_children()
        ids = []
        for child_id in children:
            child = Cat.all_cats[child_id]
            if child.outside and not child.exiled and child.moons < 12:
                child.add_to_clan()
                ids.append(child_id)
        
        return ids

    def status_change(self, new_status, resort=False):
        """ Changes the status of a cat. Additional functions are needed if you want to make a cat a leader or deputy.
            new_status = The new status of a cat. Can be 'apprentice', 'medicine cat apprentice', 'warrior'
                        'medicine cat', 'elder'.
            resort = If sorting type is 'rank', and resort is True, it will resort the cat list. This should
                    only be true for non-timeskip status changes. """
        old_status = self.status
        self.status = new_status
        self.name.status = new_status

        self.update_mentor()
        for app in self.apprentice.copy():
            fetched_cat = Cat.fetch_cat(app)
            if isinstance(fetched_cat, Cat):
                fetched_cat.update_mentor()
        
        if "request apprentice" in game.switches and game.switches['request apprentice'] and self.mentor == game.clan.your_cat.ID:
            if game.clan.your_cat.status == "queen":
                self.status =  "queen's apprentice"
            elif game.clan.your_cat.status == "mediator":
                self.status = "mediator apprentice"
            elif game.clan.your_cat.status == "medicine cat":
                self.status = "medicine cat apprentice"
            else:
                self.status = "apprentice"
            game.switches["request apprentice"] = False

        # If they have any apprentices, make sure they are still valid:
        if old_status == "medicine cat":
            game.clan.remove_med_cat(self)

        # updates mentors
        if self.status == 'apprentice':
            pass

        elif self.status == 'medicine cat apprentice':
            pass
        
        elif self.status == 'mediator apprentice':
            pass
        
        elif self.status == "queen's apprentice":
            pass

        elif self.status == 'warrior':
            if old_status == 'leader':
                if game.clan.leader:
                    if game.clan.leader.ID == self.ID:
                        game.clan.leader = None
                        game.clan.leader_predecessors += 1

                    # don't remove the check for game.clan, this is needed for tests
            if game.clan and game.clan.deputy:
                if game.clan.deputy.ID == self.ID:
                    game.clan.deputy = None
                    game.clan.deputy_predecessors += 1

        elif self.status == 'medicine cat':
            if game.clan is not None:
                game.clan.new_medicine_cat(self)

        elif self.status == 'elder':
            if old_status == 'leader':
                if game.clan.leader:
                    if game.clan.leader.ID == self.ID:
                        game.clan.leader = None
                        game.clan.leader_predecessors += 1

            if game.clan.deputy:
                if game.clan.deputy.ID == self.ID:
                    game.clan.deputy = None
                    game.clan.deputy_predecessors += 1

        elif self.status == 'mediator':
            pass

        elif self.status == 'mediator apprentice':
            pass
        
        elif self.status == 'queen':
            pass

        elif self.status == "queen's apprentice":
            pass

        # update class dictionary
        self.all_cats[self.ID] = self

        # If we have it sorted by rank, we also need to re-sort
        if game.sort_type == "rank" and resort:
            Cat.sort_cats()

    
    def rank_change_traits_skill(self, mentor):
        """Updates trait and skill upon ceremony"""  

        if self.status in ["warrior", "medicine cat", "mediator", "queen"]:
            # Give a couple doses of mentor influence:
            if mentor:
                max = randint(0, 2)
                i = 0
                while max > i:
                    i += 1
                    affect_personality = self.personality.mentor_influence(Cat.fetch_cat(mentor))
                    affect_skills = self.skills.mentor_influence(Cat.fetch_cat(mentor))
                    if affect_personality:
                        History.add_facet_mentor_influence(self, affect_personality[0], affect_personality[1], affect_personality[2])
                    if affect_skills:
                        History.add_skill_mentor_influence(self, affect_skills[0], affect_skills[1], affect_skills[2])
            
            History.add_mentor_skill_influence_strings(self)
            History.add_mentor_facet_influence_strings(self)
        return

    def manage_outside_trait(self):
        """To be run every moon on outside cats
            to keep trait and skills making sense."""
        if not (self.outside or self.exiled):
            return
        
        self.personality.set_kit(self.is_baby()) #Update kit trait stuff
        

    def describe_cat(self, short=False):
        """ Generates a string describing the cat's appearance and gender. Mainly used for generating
        the allegiances. If short is true, it will generate a very short one, with the minimal amount of information. """
        return Pelt.describe_appearance(self, short)

    def describe_eyes(self):
        if(self.genotype.lefteye == self.genotype.righteye):
            colour = self.genotype.lefteye.lower()
        else:
            colour = self.genotype.righteye.lower() + " & " + self.genotype.lefteye.lower()
               
        return colour

    def convert_history(self, died_by, scar_events):
        """
        this is to handle old history save conversions
        """
        deaths = []
        if died_by:
            for death in died_by:
                deaths.append(
                    {
                        "involved": None,
                        "text": death,
                        "moon": "?"
                    }
                )
        scars = []
        if scar_events:
            for scar in scar_events:
                scars.append(
                    {
                        "involved": None,
                        "text": scar,
                        "moon": "?"
                    }
                )
        self.history = History(
            died_by=deaths,
            scar_events=scars,
        )

    def load_history(self):
        try:
            if game.switches['clan_name'] != '':
                clanname = game.switches['clan_name']
            else:
                clanname = game.switches['clan_list'][0]
        except IndexError:
            print('WARNING: History failed to load, no Clan in game.switches?')
            return

        history_directory = get_save_dir() + '/' + clanname + '/history/'
        cat_history_directory = history_directory + self.ID + '_history.json'

        if not os.path.exists(cat_history_directory):
            self.history = History(
                beginning={},
                mentor_influence={},
                app_ceremony={},
                lead_ceremony=None,
                possible_history={},
                died_by=[],
                scar_events=[],
                murder={},
            )
            return
        try:
            with open(cat_history_directory, 'r') as read_file:
                history_data = ujson.loads(read_file.read())
                self.history = History(
                    beginning=history_data["beginning"] if "beginning" in history_data else {},
                    mentor_influence=history_data[
                        'mentor_influence'] if "mentor_influence" in history_data else {},
                    app_ceremony=history_data['app_ceremony'] if "app_ceremony" in history_data else {},
                    lead_ceremony=history_data['lead_ceremony'] if "lead_ceremony" in history_data else None,
                    possible_history=history_data['possible_history'] if "possible_history" in history_data else {},
                    died_by=history_data['died_by'] if "died_by" in history_data else [],
                    scar_events=history_data['scar_events'] if "scar_events" in history_data else [],
                    murder=history_data['murder'] if "murder" in history_data else {},
                )
        except:
            self.history = None
            print(f'WARNING: There was an error reading the history file of cat #{self} or their history file was '
                  f'empty. Default history info was given. Close game without saving if you have save information '
                  f'you\'d like to preserve!')

    def save_history(self, history_dir):
        if not os.path.exists(history_dir):
            os.makedirs(history_dir)

        history_dict = History.make_dict(self)
        try:
            game.safe_save(history_dir + '/' + self.ID + '_history.json', history_dict)
        except:
            self.history = History(
                beginning={},
                mentor_influence={},
                app_ceremony={},
                lead_ceremony=None,
                possible_history={},
                died_by=[],
                scar_events=[],
                murder={},
            )

            print(f"WARNING: saving history of cat #{self.ID} didn't work")
            

    def generate_lead_ceremony(self):
        """
        here we create a leader ceremony and add it to the history
        :param cat: cat object
        """

        # determine which dict we're pulling from
        if game.clan.followingsc == False:
            starclan = False
            ceremony_dict = LEAD_CEREMONY_DF
        else:
            starclan = True
            ceremony_dict = LEAD_CEREMONY_SC

        # ---------------------------------------------------------------------------- #
        #                                    INTRO                                     #
        # ---------------------------------------------------------------------------- #
        all_intros = ceremony_dict["intros"]

        # filter the intros
        possible_intros = []
        for intro in all_intros:
            tags = all_intros[intro]["tags"]

            if game.clan.age != 0 and "new_clan" in tags:
                continue
            elif game.clan.age == 0 and "new_clan" not in tags:
                continue

            if all_intros[intro]["lead_trait"]:
                if self.personality.trait not in all_intros[intro]["lead_trait"]:
                    continue
            possible_intros.append(all_intros[intro])

        # choose and adjust text
        chosen_intro = choice(possible_intros)
        if chosen_intro:
            intro = choice(chosen_intro["text"])
            intro = leader_ceremony_text_adjust(Cat,
                                                intro,
                                                self,
                                                )
        else:
            intro = 'this should not appear'

        # ---------------------------------------------------------------------------- #
        #                                 LIFE GIVING                                  #
        # ---------------------------------------------------------------------------- #
        life_givers = []
        dead_relations = []
        life_giving_leader = None

        # grab life givers that the cat actually knew in life and sort by amount of relationship!
        relationships = self.relationships.values()

        for rel in relationships:
            kitty = self.fetch_cat(rel.cat_to)
            if kitty and kitty.dead and kitty.status != 'newborn':
                # check where they reside
                if starclan:
                    if kitty.ID not in game.clan.starclan_cats:
                        continue
                else:
                    if kitty.ID not in game.clan.darkforest_cats:
                        continue
                # guides aren't allowed here
                if kitty == game.clan.instructor or kitty == game.clan.demon:
                    continue
                else:
                    dead_relations.append(rel)

        # sort relations by the strength of their relationship
        dead_relations.sort(
            key=lambda rel: rel.romantic_love + rel.platonic_like + rel.admiration + rel.comfortable + rel.trust, reverse=True)

        # if we have relations, then make sure we only take the top 8
        if dead_relations:
            i = 0
            for rel in dead_relations:
                if i == 8:
                    break
                if rel.cat_to.status == 'leader':
                    life_giving_leader = rel.cat_to
                    continue
                life_givers.append(rel.cat_to.ID)
                i += 1
        # check amount of life givers, if we need more, then grab from the other dead cats
        if len(life_givers) < 8:
            amount = 8 - len(life_givers)

            if starclan:
                # this part just checks how many SC cats are available, if there aren't enough to fill all the slots,
                # then we just take however many are available

                possible_sc_cats = [i for i in game.clan.starclan_cats if
                                    self.fetch_cat(i) and
                                    i not in life_givers and
                                    self.fetch_cat(i).status not in ['leader', 'newborn']]

                if len(possible_sc_cats) - 1 < amount:
                    extra_givers = possible_sc_cats
                else:
                    extra_givers = sample(possible_sc_cats, k=amount)
            else:
                #print(game.clan.darkforest_cats)
                possible_df_cats = [i for i in game.clan.darkforest_cats if
                                    self.fetch_cat(i) and
                                    i not in life_givers and
                                    self.fetch_cat(i).status not in ['leader', 'newborn']]
                if len(possible_df_cats) - 1 < amount:
                    extra_givers = possible_df_cats
                else:
                    extra_givers = sample(possible_df_cats, k=amount)

            life_givers.extend(extra_givers)

        # making sure we have a leader at the end
        ancient_leader = False
        if not life_giving_leader:
            # choosing if the life giving leader will be oldest leader or previous leader
            coin_flip = randint(1, 2)
            if coin_flip == 1:
                # pick oldest leader in SC
                ancient_leader = True
                if starclan:
                    for kitty in reversed(game.clan.starclan_cats):
                        if self.fetch_cat(kitty) and \
                            self.fetch_cat(kitty).status == 'leader':
                            life_giving_leader = kitty
                            break
                else:
                    for kitty in reversed(game.clan.darkforest_cats):
                        if self.fetch_cat(kitty) and \
                            self.fetch_cat(kitty).status == 'leader':
                            life_giving_leader = kitty
                            break
            else:
                # pick previous leader
                if starclan:
                    for kitty in game.clan.starclan_cats:
                        if self.fetch_cat(kitty) and \
                            self.fetch_cat(kitty).status == 'leader':
                            life_giving_leader = kitty
                            break
                else:
                    for kitty in game.clan.darkforest_cats:
                        if self.fetch_cat(kitty) and \
                            self.fetch_cat(kitty).status == 'leader':
                            life_giving_leader = kitty
                            break

        if life_giving_leader:
            life_givers.append(life_giving_leader)

        # check amount again, if more are needed then we'll add the ghost-y cats at the end
        if len(life_givers) < 9:
            unknown_blessing = True
            extra_lives = str(9 - len(life_givers))
        else:
            unknown_blessing = False
            extra_lives = str(9 - len(life_givers))

        possible_lives = ceremony_dict["lives"]
        lives = []
        used_lives = []
        used_virtues = []
        trait = self.personality.trait
        cluster, second_cluster = get_cluster(trait)
        
        for giver in life_givers:
            giver_cat = self.fetch_cat(giver)
            if not giver_cat:
                continue
            trait = giver_cat.personality.trait
            cluster2, second_cluster2 = get_cluster(trait)
            life_list = []
            if game.clan.your_cat.ID == self.ID:
                victim_in_lifegiver = False
                if game.clan.your_cat.history:
                    if game.clan.your_cat.history.murder and "murdered" in tags:
                        if "is_murderer" in game.clan.your_cat.history.murder:
                            if len(game.clan.your_cat.history.murder["is_murderer"]) > 0:
                                for i in game.clan.your_cat.history.murder["is_murderer"]:
                                    if i['victim'] == giver_cat.ID:
                                        victim_in_lifegiver = True
                                        
            for life in possible_lives:
                tags = possible_lives[life]["tags"]
                rank = giver_cat.status
                if game.clan.your_cat.ID == self.ID:
                    if victim_in_lifegiver and "murdered" not in tags:
                        continue
                    if not victim_in_lifegiver and "murdered" in tags:
                        continue
                elif "murdered" in tags:
                    continue
                if "unknown_blessing" in tags:
                    continue
                if "guide" in tags and giver_cat != game.clan.instructor and giver_cat != game.clan.demon:
                    continue
                if game.clan.age != 0 and "new_clan" in tags:
                    continue
                elif game.clan.age == 0 and "new_clan" not in tags:
                    continue
                if "old_leader" in tags and not ancient_leader:
                    continue
                if "leader_parent" in tags and giver_cat.ID not in self.get_parents():
                    continue
                elif "leader_child" in tags and giver_cat.ID not in self.get_children():
                    continue
                elif "leader_sibling" in tags and giver_cat.ID not in self.get_siblings():
                    continue
                elif "leader_mate" in tags and giver_cat.ID not in self.mate:
                    continue
                elif "leader_former_mate" in tags and giver_cat.ID not in self.previous_mates:
                    continue
                if "leader_mentor" in tags and giver_cat.ID not in self.former_mentor:
                    continue
                if "leader_apprentice" in tags and giver_cat.ID not in self.former_apprentices:
                    continue

                if possible_lives[life]["rank"]:
                    if rank not in possible_lives[life]["rank"]:
                        continue
                if possible_lives[life]["lead_trait"]:
                    if (self.personality.trait not in possible_lives[life]["lead_trait"]) and (cluster not in possible_lives[life]["lead_trait"]) and (second_cluster not in possible_lives[life]["lead_trait"]):
                        continue
                if possible_lives[life]["star_trait"]:
                    if giver_cat.personality.trait not in possible_lives[life]["star_trait"] and (cluster2 not in possible_lives[life]["star_trait"]) and (second_cluster2 not in possible_lives[life]["star_trait"]):
                        continue
                life_list.extend([i for i in possible_lives[life]["life_giving"]])

            i = 0
            chosen_life = {}
            while i < 10:
                attempted = []
                if life_list:
                    chosen_life = choice(life_list)
                    if chosen_life not in used_lives and chosen_life not in attempted:
                        break
                    else:
                        attempted.append(chosen_life)
                    i += 1
                else:
                    print(
                        f'WARNING: life list had no items for giver #{giver_cat.ID}. Using default life. If you are a beta tester, please report and ping scribble along with all the info you can about the giver cat mentioned in this warning.')
                    chosen_life = ceremony_dict["default_life"]
                    break
                
            
            used_lives.append(chosen_life)
            if "virtue" in chosen_life:
                poss_virtues = [i for i in chosen_life["virtue"] if i not in used_virtues]
                if not poss_virtues:
                    poss_virtues = ['faith', 'friendship', 'love', 'strength']
                virtue = choice(poss_virtues)
                used_virtues.append(virtue)
            else:
                virtue = None

            lives.append(leader_ceremony_text_adjust(Cat,
                                                     chosen_life["text"],
                                                     leader=self,
                                                     life_giver=giver,
                                                     virtue=virtue,
                                                     ))
        if unknown_blessing:
            possible_blessing = []
            for life in possible_lives:
                tags = possible_lives[life]["tags"]

                if "unknown_blessing" not in tags:
                    continue

                if possible_lives[life]["lead_trait"]:
                    if self.personality.trait not in possible_lives[life]["lead_trait"]:
                        continue
                possible_blessing.append(possible_lives[life])
            chosen_blessing = choice(possible_blessing)
            chosen_text = choice(chosen_blessing["life_giving"])
            lives.append(leader_ceremony_text_adjust(Cat,
                                                     chosen_text["text"],
                                                     leader=self,
                                                     virtue=chosen_text["virtue"],
                                                     extra_lives=extra_lives,
                                                     ))
        all_lives = "<br><br>".join(lives)

        # ---------------------------------------------------------------------------- #
        #                                    OUTRO                                     #
        # ---------------------------------------------------------------------------- #

        # get the outro
        all_outros = ceremony_dict["outros"]

        possible_outros = []
        for outro in all_outros:
            tags = all_outros[outro]["tags"]

            if game.clan.age != 0 and "new_clan" in tags:
                continue
            elif game.clan.age == 0 and "new_clan" not in tags:
                continue

            if all_outros[outro]["lead_trait"]:
                if self.personality.trait not in all_outros[outro]["lead_trait"]:
                    continue
            possible_outros.append(all_outros[outro])

        chosen_outro = choice(possible_outros)

        if chosen_outro:
            if life_givers:
                giver = life_givers[-1]
            else:
                giver = None
            outro = choice(chosen_outro["text"])
            outro = leader_ceremony_text_adjust(Cat,
                                                outro,
                                                leader=self,
                                                life_giver=giver,
                                                )
        else:
            outro = 'this should not appear'

        full_ceremony = "<br><br>".join([intro, all_lives, outro])
        return full_ceremony

    # ---------------------------------------------------------------------------- #
    #                              moon skip functions                             #
    # ---------------------------------------------------------------------------- #

    def one_moon(self):
        """Handles a moon skip for an alive cat. """
        old_age = self.age
        self.moons += 1
        if self.moons == 1 and self.status == "newborn":
            self.status = 'kitten'
        elif self.moons == 0 and self.status == "kitten":
            self.status = 'newborn'
        self.in_camp = 1
        
        if self.exiled or self.outside:
            # this is handled in events.py
            self.personality.set_kit(self.is_baby())
            self.thoughts()
            return

        if self.dead:
            self.thoughts()
            return
        
        if old_age != self.age:
            # Things to do if the age changes
            self.personality.facet_wobble(max=2)
        
        # Set personality to correct type
        self.personality.set_kit(self.is_baby())
        # Upon age-change

        if self.status in ['apprentice', 'mediator apprentice', 'medicine cat apprentice', "queen's apprentice"]:
            self.update_mentor()

    def thoughts(self):
        """ Generates a thought for the cat, which displays on their profile. """
        all_cats = self.all_cats
        other_cat = choice(list(all_cats.keys()))
        game_mode = game.switches['game_mode']
        biome = game.switches['biome']
        camp = game.switches['camp_bg']
        dead_chance = getrandbits(4)
        season = None
        if game.clan:
            try:
                season = game.clan.current_season
            except:
                season = None
        

        # this figures out where the cat is
        where_kitty = None
        if not self.dead and not self.outside:
            where_kitty = "inside"
        elif self.dead and not self.df and not self.outside:
            where_kitty = 'starclan'
        elif self.dead and self.df:
            where_kitty = 'hell'
        elif self.dead and self.outside:
            where_kitty = 'UR'
        elif not self.dead and self.outside:
            where_kitty = 'outside'
        # get other cat
        i = 0
        # for cats inside the clan
        if where_kitty == 'inside':
            while other_cat == self.ID and len(all_cats) > 1 \
                    or (all_cats.get(other_cat).dead and dead_chance != 1) \
                    or (other_cat not in self.relationships):
                other_cat = choice(list(all_cats.keys()))
                i += 1
                if i > 100:
                    other_cat = None
                    break
        # for dead cats
        elif where_kitty in ['starclan', 'hell', 'UR']:
            while other_cat == self.ID and len(all_cats) > 1:
                other_cat = choice(list(all_cats.keys()))
                i += 1
                if i > 100:
                    other_cat = None
                    break
        # for cats currently outside
        # it appears as for now, kittypets and loners can only think about outsider cats
        elif where_kitty == 'outside':
            while other_cat == self.ID and len(all_cats) > 1 \
                    or (other_cat not in self.relationships):
                '''or (self.status in ['kittypet', 'loner'] and not all_cats.get(other_cat).outside):'''
                other_cat = choice(list(all_cats.keys()))
                i += 1
                if i > 100:
                    other_cat = None
                    break

        other_cat = all_cats.get(other_cat)

        # get chosen thought
        chosen_thought = Thoughts.get_chosen_thought(self, other_cat, game_mode, biome, season, camp)

        chosen_thought = event_text_adjust(Cat, chosen_thought, self, other_cat)
        # insert thought
        self.thought = str(chosen_thought)

    def relationship_interaction(self):
        """Randomly choose a cat of the Clan and have a interaction with them."""
        # if the cat has no relationships, skip
        if not self.relationships or len(self.relationships) < 1:
            return

        cats_to_choose = [iter_cat for iter_cat in Cat.all_cats.values() if iter_cat.ID != self.ID and \
                          not iter_cat.outside and not iter_cat.exiled and not iter_cat.dead]
        # if there are not cats to interact, stop
        if len(cats_to_choose) < 1:
            return

        chosen_cat = choice(cats_to_choose)
        if chosen_cat.ID not in self.relationships:
            self.create_one_relationship(chosen_cat)
        relevant_relationship = self.relationships[chosen_cat.ID]
        relevant_relationship.start_interaction()

        if game.game_mode == "classic":
            return
        # handle contact with ill cat if
        if self.is_ill():
            relevant_relationship.cat_to.contact_with_ill_cat(self)
        if relevant_relationship.cat_to.is_ill():
            self.contact_with_ill_cat(relevant_relationship.cat_to)

    def moon_skip_illness(self, illness):
        """handles the moon skip for illness"""
        if not self.is_ill():
            return True

        if self.illnesses[illness]["event_triggered"]:
            self.illnesses[illness]["event_triggered"] = False
            return True

        mortality = self.illnesses[illness]["mortality"]

        # leader should have a higher chance of death
        if self.status == "leader" and mortality != 0:
            mortality = int(mortality * 0.7)
            if mortality == 0:
                mortality = 1

        if mortality and not int(random() * mortality):
            if self.status == "leader":
                self.leader_death_heal = True
                game.clan.leader_lives -= 1
                if game.clan.leader_lives > 0:
                    text = f"{self.name} lost a life to {illness}."
                    # game.health_events_list.append(text)
                    # game.birth_death_events_list.append(text)
                    game.cur_events_list.append(Single_Event(text, ["birth_death", "health"], game.clan.leader.ID))
                elif game.clan.leader_lives <= 0:
                    text = f"{self.name} lost their last life to {illness}."
                    # game.health_events_list.append(text)
                    # game.birth_death_events_list.append(text)
                    game.cur_events_list.append(Single_Event(text, ["birth_death", "health"], game.clan.leader.ID))
            self.die()
            return False
        if "moon_start" in self.illnesses[illness]:
            moons_with = game.clan.age - self.illnesses[illness]["moon_start"]
            
        else:
            moons_with = 0

        if self.illnesses[illness]["duration"] - moons_with <= 0:
            self.healed_condition = True
            return False

    def moon_skip_injury(self, injury):
        """handles the moon skip for injury"""
        if not self.is_injured():
            return True

        if self.injuries[injury]["event_triggered"] is True:
            self.injuries[injury]["event_triggered"] = False
            return True

        mortality = self.injuries[injury]["mortality"]

        # leader should have a higher chance of death
        if self.status == "leader" and mortality != 0:
            mortality = int(mortality * 0.7)
            if mortality == 0:
                mortality = 1

        if mortality and not int(random() * mortality):
            if self.status == 'leader':
                game.clan.leader_lives -= 1
            self.die()
            return False
        moons_with = 0
        if "moon_start" in self.injuries[injury]:
            moons_with = game.clan.age - self.injuries[injury]["moon_start"]


        # if the cat has an infected wound, the wound shouldn't heal till the illness is cured
        if not self.injuries[injury]["complication"] and self.injuries[injury]["duration"] - moons_with <= 0:
            self.healed_condition = True
            return False

    def moon_skip_permanent_condition(self, condition):
        """handles the moon skip for permanent conditions"""
        if not self.is_disabled():
            return "skip"

        if self.permanent_condition[condition]["event_triggered"]:
            self.permanent_condition[condition]["event_triggered"] = False
            return "skip"

        mortality = self.permanent_condition[condition]["mortality"]
        moons_until = self.permanent_condition[condition]["moons_until"]
        born_with = self.permanent_condition[condition]["born_with"]

        # handling the countdown till a congenital condition is revealed
        if moons_until is not None and moons_until >= 0 and born_with is True:
            self.permanent_condition[condition]["moons_until"] = int(moons_until - 1)
            self.permanent_condition[condition]["moons_with"] = 0
            if self.permanent_condition[condition]["moons_until"] != -1:
                return "skip"
        if self.permanent_condition[condition]["moons_until"] == -1 and \
                self.permanent_condition[condition]["born_with"] is True:
            self.permanent_condition[condition]["moons_until"] = -2
            return "reveal"

        # leader should have a higher chance of death
        if self.status == "leader" and mortality != 0:
            mortality = int(mortality * 0.7)
            if mortality == 0:
                mortality = 1

        if mortality and not int(random() * mortality):
            if self.status == 'leader':
                game.clan.leader_lives -= 1
            self.die()
            return "continue"

    # ---------------------------------------------------------------------------- #
    #                                   relative                                   #
    # ---------------------------------------------------------------------------- #
    def get_parents(self):
        """Returns list containing parents of cat(id)."""
        if not self.inheritance:
            self.inheritance = Inheritance(self)
        return self.inheritance.parents.keys()

    def get_siblings(self):
        """Returns list of the siblings(id)."""
        if not self.inheritance:
            self.inheritance = Inheritance(self)
        return self.inheritance.siblings.keys()

    def get_children(self):
        """Returns list of the children (ids)."""
        if not self.inheritance:
            self.inheritance = Inheritance(self)
        return self.inheritance.kits.keys()

    def is_grandparent(self, other_cat: Cat):
        """Check if the cat is the grandparent of the other cat."""
        if not self.inheritance:
            self.inheritance = Inheritance(self)
        return other_cat.ID in self.inheritance.grand_kits.keys()

    def is_parent(self, other_cat: Cat):
        """Check if the cat is the parent of the other cat."""
        if not self.inheritance:
            self.inheritance = Inheritance(self)
        return other_cat.ID in self.inheritance.kits.keys()

    def is_sibling(self, other_cat: Cat):
        """Check if the cats are siblings."""
        if not self.inheritance:
            self.inheritance = Inheritance(self)
        return other_cat.ID in self.inheritance.siblings.keys()

    def is_littermate(self, other_cat: Cat):
        """Check if the cats are littermates."""
        if other_cat.ID not in self.inheritance.siblings.keys():
            return False
        litter_mates = [key for key, value in self.inheritance.siblings.items() if
                        "litter mates" in value["additional"]]
        return other_cat.ID in litter_mates

    def is_uncle_aunt(self, other_cat):
        """Check if the cats are related as uncle/aunt and niece/nephew."""
        if not self.inheritance:
            self.inheritance = Inheritance(self)
        return other_cat.ID in self.inheritance.siblings_kits.keys()

    def is_cousin(self, other_cat):
        if not self.inheritance:
            self.inheritance = Inheritance(self)
        return other_cat.ID in self.inheritance.cousins.keys()

    def is_related(self, other_cat, cousin_allowed):
        """Checks if the given cat is related to the current cat, according to the inheritance."""
        if not self.inheritance:
            self.inheritance = Inheritance(self)
        if cousin_allowed:
            return other_cat.ID in self.inheritance.all_but_cousins
        return other_cat.ID in self.inheritance.all_involved

    def get_relatives(self, cousin_allowed=True) -> list:
        """Returns a list of ids of all nearly related ancestors."""
        if not self.inheritance:
            self.inheritance = Inheritance(self)
        if cousin_allowed:
            return self.inheritance.all_involved
        return self.inheritance.all_but_cousins

    # ---------------------------------------------------------------------------- #
    #                                  conditions                                  #
    # ---------------------------------------------------------------------------- #

    def get_ill(self, name, event_triggered=False, lethal=True, severity='default', grief_cat=None):
        """
        use to make a cat ill.
        name = name of the illness you want the cat to get
        event_triggered = make True to have this illness skip the illness_moonskip for 1 moon
        lethal = set True to leave the illness mortality rate at its default level.
                 set False to force the illness to have 0 mortality
        severity = leave 'default' to keep default severity, otherwise set to the desired severity
                   ('minor', 'major', 'severe')
        """

        if name not in ILLNESSES:
            print(f"WARNING: {name} is not in the illnesses collection.")
            return
        if name == 'kittencough' and self.status != 'kitten':
            return

        illness = ILLNESSES[name]
        mortality = illness["mortality"][self.age]
        med_mortality = illness["medicine_mortality"][self.age]
        if severity == 'default':
            illness_severity = illness["severity"]
        else:
            illness_severity = severity

        duration = illness['duration']
        med_duration = illness['medicine_duration']

        amount_per_med = get_amount_cat_for_one_medic(game.clan)

        if medical_cats_condition_fulfilled(Cat.all_cats.values(), amount_per_med):
            duration = med_duration
        if severity != 'minor':
            duration += randrange(-1, 1)
        if duration == 0:
            duration = 1

        if game.clan and game.clan.game_mode == "cruel season":
            if mortality != 0:
                mortality = int(mortality * 0.5)
                med_mortality = int(med_mortality * 0.5)

        #         # to prevent an illness gets no mortality, check and set it to 1 if needed
        #         if mortality == 0 or med_mortality == 0:
        #             mortality = 1
        #             med_mortality = 1
        if lethal is False:
            mortality = 0

        new_illness = Illness(
            name=name,
            severity=illness_severity,
            mortality=mortality,
            infectiousness=illness["infectiousness"],
            duration=duration,
            medicine_duration=illness["medicine_duration"],
            medicine_mortality=med_mortality,
            risks=illness["risks"],
            event_triggered=event_triggered,
            grief_cat = grief_cat
        )

        if new_illness.name not in self.illnesses:
            self.illnesses[new_illness.name] = {
                "severity": new_illness.severity,
                "mortality": new_illness.current_mortality,
                "infectiousness": new_illness.infectiousness,
                "duration": new_illness.duration,
                "moon_start": game.clan.age if game.clan else 0,
                "risks": new_illness.risks,
                "event_triggered": new_illness.new
            }
            if grief_cat:
                self.illnesses[new_illness.name]['grief_cat'] = grief_cat.ID

    def get_injured(self, name, event_triggered=False, lethal=True, severity='default'):
        if game.clan and game.clan.game_mode == "classic":
            return
        
        if name not in INJURIES:
            if name not in INJURIES:
                print(f"WARNING: {name} is not in the injuries collection.")
            return

        if name == 'mangled tail' and 'NOTAIL' in self.pelt.scars:
            return
        if name == 'torn ear' and 'NOEAR' in self.pelt.scars:
            return

        injury = INJURIES[name]
        mortality = injury["mortality"][self.age]
        duration = injury['duration']
        med_duration = injury['medicine_duration']

        if severity == 'default':
            injury_severity = injury["severity"]
        else:
            injury_severity = severity

        if medical_cats_condition_fulfilled(Cat.all_cats.values(), get_amount_cat_for_one_medic(game.clan)):
            duration = med_duration
        if severity != 'minor':
            duration += randrange(-1, 1)
        if duration == 0:
            duration = 1

        if mortality != 0:
            if game.clan and game.clan.game_mode == "cruel season":
                mortality = int(mortality * 0.5)

        #         if mortality == 0:
        #             mortality = 1
        if lethal is False:
            mortality = 0

        new_injury = Injury(
            name=name,
            severity=injury_severity,
            duration=injury["duration"],
            medicine_duration=duration,
            mortality=mortality,
            risks=injury["risks"],
            illness_infectiousness=injury["illness_infectiousness"],
            also_got=injury["also_got"],
            cause_permanent=injury["cause_permanent"],
            event_triggered=event_triggered
        )

        if new_injury.name not in self.injuries:
            self.injuries[new_injury.name] = {
                "severity": new_injury.severity,
                "mortality": new_injury.current_mortality,
                "duration": new_injury.duration,
                "moon_start": game.clan.age if game.clan else 0,
                "illness_infectiousness": new_injury.illness_infectiousness,
                "risks": new_injury.risks,
                "complication": None,
                "cause_permanent": new_injury.cause_permanent,
                "event_triggered": new_injury.new
            }

        if len(new_injury.also_got) > 0 and not int(random() * 5):
            avoided = False
            if 'blood loss' in new_injury.also_got and len(get_med_cats(Cat)) != 0:
                clan_herbs = set()
                needed_herbs = {"horsetail", "raspberry", "marigold", "cobwebs"}
                clan_herbs.update(game.clan.herbs.keys())
                herb_set = needed_herbs.intersection(clan_herbs)
                usable_herbs = []
                usable_herbs.extend(herb_set)

                if usable_herbs:
                    # deplete the herb
                    herb_used = choice(usable_herbs)
                    game.clan.herbs[herb_used] -= 1
                    if game.clan.herbs[herb_used] <= 0:
                        game.clan.herbs.pop(herb_used)
                    avoided = True
                    text = f"{herb_used.capitalize()} was used to stop blood loss for {self.name}."
                    game.herb_events_list.append(text)

            if not avoided:
                self.also_got = True
                additional_injury = choice(new_injury.also_got)
                if additional_injury in INJURIES:
                    self.additional_injury(additional_injury)
                else:
                    self.get_ill(additional_injury, event_triggered=True)
        else:
            self.also_got = False

    def additional_injury(self, injury):
        self.get_injured(injury, event_triggered=True)

    def congenital_condition(self, cat):
        possible_conditions = []

        for condition in PERMANENT:
            possible = PERMANENT[condition]
            if possible["congenital"] in ['always', 'sometimes']:
                possible_conditions.append(condition)

        new_condition = choice(possible_conditions)

        if new_condition == "born without a leg":
            cat.pelt.scars.append('NOPAW')
        elif new_condition == "born without a tail":
            cat.pelt.scars.append('NOTAIL')

        self.get_permanent_condition(new_condition, born_with=True)

    def get_permanent_condition(self, name, born_with=False, event_triggered=False):
        with open(f"resources/dicts/conditions/permanent_conditions.json", 'r') as read_file:
            PERMANENT = ujson.loads(read_file.read())   
        if name not in PERMANENT:
            print(str(self.name), f"WARNING: {name} is not in the permanent conditions collection.")
            return

        # remove accessories if need be
        if ('NOTAIL' in self.pelt.scars or (self.phenotype.bobtailnr > 0 and self.phenotype.bobtailnr < 5)) and self.pelt.accessory in ['RED FEATHERS', 'BLUE FEATHERS', 'JAY FEATHERS', "SEAWEED", "DAISY CORSAGE"]:
            self.pelt.accessory = None
        if 'HALFTAIL' in self.pelt.scars and self.pelt.accessory in ['RED FEATHERS', 'BLUE FEATHERS', 'JAY FEATHERS', "SEAWEED", "DAISY CORSAGE"]:
            self.pelt.accessory = None

        condition = PERMANENT[name]
        new_condition = False
        mortality = condition["mortality"][self.age]
        if mortality != 0:
            if game.clan and game.clan.game_mode == "cruel season":
                mortality = int(mortality * 0.65)

        if condition['congenital'] == 'always':
            born_with = True
        moons_until = condition["moons_until"]
        if born_with and moons_until != 0:
            moons_until = randint(moons_until - 1, moons_until + 1)  # creating a range in which a condition can present
            if moons_until < 0:
                moons_until = 0

        if born_with and self.status not in ['kitten', 'newborn']:
            moons_until = -2
        elif born_with is False:
            moons_until = 0

        if name == "paralyzed":
            self.pelt.paralyzed = True

        new_perm_condition = PermanentCondition(
            name=name,
            severity=condition["severity"],
            congenital=condition["congenital"],
            moons_until=moons_until,
            mortality=mortality,
            risks=condition["risks"],
            illness_infectiousness=condition["illness_infectiousness"],
            event_triggered=event_triggered
        )

        if new_perm_condition.name not in self.permanent_condition:
            self.permanent_condition[new_perm_condition.name] = {
                "severity": new_perm_condition.severity,
                "born_with": born_with,
                "moons_until": new_perm_condition.moons_until,
                "moon_start": game.clan.age if game.clan else 0,
                "mortality": new_perm_condition.current_mortality,
                "illness_infectiousness": new_perm_condition.illness_infectiousness,
                "risks": new_perm_condition.risks,
                "complication": None,
                "event_triggered": new_perm_condition.new
            }
            new_condition = True
        return new_condition

    def not_working(self):
        """returns True if the cat cannot work, False if the cat can work"""
        for illness in self.illnesses:
            if self.illnesses[illness]['severity'] != 'minor':
                return True
        for injury in self.injuries:
            if self.injuries[injury]['severity'] != 'minor':
                return True
        return False

    def not_work_because_hunger(self):
        """returns True if the only condition, why the cat cannot work is because of starvation"""
        non_minor_injuries = [injury for injury in self.injuries if self.injuries[injury]['severity'] != 'minor']
        if len(non_minor_injuries) > 0:
            return False
        non_minor_illnesses = [illness for illness in self.illnesses if self.illnesses[illness]['severity'] != 'minor']
        if "starving" in non_minor_illnesses and len(non_minor_illnesses) == 1:
            return True
        else:
            return False
    
    def retire_cat(self):
        """This is only for cats that retire due to health condition"""
        
        #There are some special tasks we need to do for apprentice
        # Note that although you can unretire cats, they will be a full warrior/med_cat/mediator

        if self.moons > 6 and self.status in ["apprentice", "medicine cat apprentice", "mediator apprentice", "queen's apprentice"]:
            _ment = Cat.fetch_cat(self.mentor) if self.mentor else None
            self.status_change("warrior") # Temp switch them to warrior, so the following step will work
            self.rank_change_traits_skill(_ment)

        self.status_change("elder")

        return

    def is_ill(self):
        is_ill = True
        if len(self.illnesses) <= 0:
            is_ill = False
        return is_ill is not False

    def is_injured(self):
        is_injured = True
        if len(self.injuries) <= 0:
            is_injured = False
        return is_injured is not False

    def is_disabled(self):
        is_disabled = True
        if len(self.permanent_condition) <= 0:
            is_disabled = False
        return is_disabled is not False

    def contact_with_ill_cat(self, cat: Cat):
        """handles if one cat had contact with an ill cat"""

        infectious_illnesses = []
        if self.is_ill() or cat is None or not cat.is_ill():
            return
        elif cat.is_ill():
            for illness in cat.illnesses:
                if cat.illnesses[illness]["infectiousness"] != 0:
                    infectious_illnesses.append(illness)
            if len(infectious_illnesses) == 0:
                return

        for illness in infectious_illnesses:
            illness_name = illness
            rate = cat.illnesses[illness]["infectiousness"]
            if self.is_injured():
                for y in self.injuries:
                    illness_infect = list(
                        filter(lambda ill: ill["name"] == illness_name, self.injuries[y]["illness_infectiousness"]))
                    if illness_infect is not None and len(illness_infect) > 0:
                        illness_infect = illness_infect[0]
                        rate -= illness_infect["lower_by"]

                    # prevent rate lower 0 and print warning message
                    if rate < 0:
                        print(
                            f"WARNING: injury {self.injuries[y]['name']} has lowered chance of {illness_name} infection to {rate}")
                        rate = 1

            if not random() * rate:
                text = f"{self.name} had contact with {cat.name} and now has {illness_name}."
                # game.health_events_list.append(text)
                game.cur_events_list.append(Single_Event(text, "health", [self.ID, cat.ID]))
                self.get_ill(illness_name)

    def save_condition(self):
        # save conditions for each cat
        clanname = None
        if game.switches['clan_name'] != '':
            clanname = game.switches['clan_name']
        elif len(game.switches['clan_name']) > 0:
            clanname = game.switches['clan_list'][0]
        elif game.clan is not None:
            clanname = game.clan.name

        condition_directory = get_save_dir() + '/' + clanname + '/conditions'
        condition_file_path = condition_directory + '/' + self.ID + '_conditions.json'

        if (not self.is_ill() and not self.is_injured() and not self.is_disabled()) or self.dead or self.outside:
            if os.path.exists(condition_file_path):
                os.remove(condition_file_path)
            return

        conditions = {}

        if self.is_ill():
            conditions["illnesses"] = self.illnesses

        if self.is_injured():
            conditions["injuries"] = self.injuries

        if self.is_disabled():
            conditions["permanent conditions"] = self.permanent_condition

        game.safe_save(condition_file_path, conditions)

    def load_conditions(self):
        if game.switches['clan_name'] != '':
            clanname = game.switches['clan_name']
        else:
            clanname = game.switches['clan_list'][0]

        condition_directory = get_save_dir() + '/' + clanname + '/conditions/'
        condition_cat_directory = condition_directory + self.ID + '_conditions.json'
        if not os.path.exists(condition_cat_directory):
            return

        try:
            with open(condition_cat_directory, 'r') as read_file:
                rel_data = ujson.loads(read_file.read())
                self.illnesses = rel_data.get("illnesses", {})
                self.injuries = rel_data.get("injuries", {})
                self.permanent_condition = rel_data.get("permanent conditions", {})

            if "paralyzed" in self.permanent_condition and not self.pelt.paralyzed:
                self.pelt.paralyzed = True

        except Exception as e:
            print(f"WARNING: There was an error reading the condition file of cat #{self}.\n", e)

    # ---------------------------------------------------------------------------- #
    #                                    mentor                                    #
    # ---------------------------------------------------------------------------- #

    def is_valid_mentor(self, potential_mentor: Cat):
        # Dead or outside cats can't be mentors
        if potential_mentor.dead or potential_mentor.outside:
            return False
        # Match jobs
        if self.status == 'medicine cat apprentice' and potential_mentor.status != 'medicine cat':
            return False
        if self.status == 'apprentice' and potential_mentor.status not in [
            'leader', 'deputy', 'warrior'
        ]:
            return False
        if self.status == 'mediator apprentice' and potential_mentor.status != 'mediator':
            return False
        if self.status == "queen's apprentice" and potential_mentor.status != 'queen':
            return False
        
        if potential_mentor.moons <= 0:
            return False
        
        if game.clan and game.clan.your_cat and game.clan.age == 0 and potential_mentor.ID == game.clan.your_cat.ID:
            return False

        # If not an app, don't need a mentor
        if 'apprentice' not in self.status:
            return False
        # Dead cats don't need mentors
        if self.dead or self.outside or self.exiled or self.shunned > 0:
            return False
        return True

    def __remove_mentor(self):
        """Should only be called by update_mentor, also sets fields on mentor."""
        if not self.mentor:
            return
        mentor_cat = Cat.fetch_cat(self.mentor)
        if not mentor_cat:
            return
        if self.ID in mentor_cat.apprentice:
            mentor_cat.apprentice.remove(self.ID)
        if self.moons > 6 and self.ID not in mentor_cat.former_apprentices:
            mentor_cat.former_apprentices.append(self.ID)
        if self.moons > 6 and mentor_cat.ID not in self.former_mentor:
            self.former_mentor.append(mentor_cat.ID)
        self.mentor = None

    def __add_mentor(self, new_mentor_id: str):
        """Should only be called by update_mentor, also sets fields on mentor."""
        # reset patrol number
        self.patrol_with_mentor = 0
        self.mentor = new_mentor_id
        mentor_cat = Cat.fetch_cat(self.mentor)
        if not mentor_cat:
            return
        if self.ID not in mentor_cat.apprentice:
            mentor_cat.apprentice.append(self.ID)

    def update_mentor(self, new_mentor: Any = None):
        """Takes mentor's ID as argument, mentor could just be set via this function."""
        # No !!
        if isinstance(new_mentor, Cat):
            print(
                "Everything is terrible!! (new_mentor {new_mentor} is a Cat D:)")
            return
        # Check if cat can have a mentor
        illegible_for_mentor = self.dead or self.outside or self.exiled or self.shunned > 0 or self.dead_for > 1 or self.status not in ["apprentice",
                                                                                                                                        "mediator apprentice",
                                                                                                                                        "medicine cat apprentice",
                                                                                                                                        "queen's apprentice"]
        if illegible_for_mentor:
            self.__remove_mentor()
            return
        # If eligible, cat should get a mentor.
        if new_mentor:
            self.__remove_mentor()
            self.__add_mentor(new_mentor)

        # Check if current mentor is valid
        if self.mentor:
            mentor_cat = Cat.fetch_cat(self.mentor)  # This will return None if there is no current mentor
            if mentor_cat and not self.is_valid_mentor(mentor_cat):
                self.__remove_mentor()

        # Need to pick a random mentor if not specified
        if not self.mentor:
            potential_mentors = []
            priority_mentors = []
            for cat in self.all_cats.values():
                if self.is_valid_mentor(cat):
                    potential_mentors.append(cat)
                    if not cat.apprentice and not cat.not_working():
                        priority_mentors.append(cat)
            # First try for a cat who currently has no apprentices and is working
            if 'request apprentice' in game.switches:
                if game.switches['request apprentice'] and self.moons == 6:
                    new_mentor = game.clan.your_cat
                else:
                    if priority_mentors:  # length of list > 0
                        new_mentor = choice(priority_mentors)
                    elif potential_mentors:  # length of list > 0
                        new_mentor = choice(potential_mentors)
            elif priority_mentors:  # length of list > 0
                new_mentor = choice(priority_mentors)
            elif potential_mentors:  # length of list > 0
                new_mentor = choice(potential_mentors)
            if new_mentor:
                self.__add_mentor(new_mentor.ID)
    
    def update_df_mentor(self):
        """Handles giving clan members df mentors"""
        if not self.joined_df or self.dead or self.df_mentor:
            return
        
        potential_mentors = []
        for c in Cat.all_cats_list:
            if c.dead and c.df and c.moons >= 6 and self.ID != c.ID:
                potential_mentors.append(c)

        priority_mentors = []
        for c in potential_mentors: 
            if len(self.df_apprentices) == 0:
                priority_mentors.append(c)

        if priority_mentors:
            df_mentor = choice(priority_mentors)
            self.df_mentor = df_mentor.ID
            df_mentor.df_apprentices.append(self.ID)
        elif potential_mentors:
            df_mentor = choice(potential_mentors)
            self.df_mentor = df_mentor.ID
            df_mentor.df_apprentices.append(self.ID)

    # ---------------------------------------------------------------------------- #
    #                                 relationships                                #
    # ---------------------------------------------------------------------------- #
    def is_potential_mate(self,
                          other_cat: Cat,
                          for_love_interest: bool = False,
                          age_restriction: bool = True,
                          first_cousin_mates:bool = False,
                          ignore_no_mates:bool=False):
        """
            Checks if this cat is potential mate for the other cat.
            There are no restrictions if the current cat already has a mate or not (this allows poly-mates).
        """
        # just to be sure, check if it is not the same cat
        if self.ID == other_cat.ID:
            return False
        
        #No Mates Check
        if not ignore_no_mates and (self.no_mates or other_cat.no_mates):
            return False

        # Inheritance check
        if self.is_related(other_cat, game.clan.clan_settings["first cousin mates"]):
            return False

        # check exiled, outside, and dead cats
        if (self.dead != other_cat.dead) or self.outside or other_cat.outside:
            return False

        # check for age
        if age_restriction:
            if (self.moons < 14 or other_cat.moons < 14) and not for_love_interest:
                return False

            # the +1 is necessary because both might not already aged up
            # if only one is aged up at this point, later they are more moons apart than the setting defined
            # game_config boolian "override_same_age_group" disables the same-age group check.
            if game.config["mates"].get("override_same_age_group", False) or self.age != other_cat.age:
                if abs(self.moons - other_cat.moons)> game.config["mates"]["age_range"] + 1:
                    return False

        age_restricted_ages = ["newborn", "kitten", "adolescent"]
        if self.age in age_restricted_ages or other_cat.age in age_restricted_ages:
            if self.age != other_cat.age:
                return False

        # check for mentor

        # Current mentor
        if other_cat.ID in self.apprentice or self.ID in other_cat.apprentice:
            return False
        
        is_former_mentor = (other_cat.ID in self.former_apprentices or self.ID in other_cat.former_apprentices)
        if is_former_mentor and not game.clan.clan_settings['romantic with former mentor']:
            return False

        return True
    
    def is_dateable(self,
                    other_cat: Cat,
                    age_restriction: bool = True,
                    ignore_no_mates: bool = False
                    ):

        """
            LifeGen-specific function to see if a cat can be dated/flirted with.
            Heavily based on is_potential_mate with some key differences.
            The age limit is 12 moons instead of 14 since the player is allowed to make that choice.
            Adolescents are allowed to flirt with each other.
            This function should not be used in place of is_potential_mate.
        """
        
        # check to make sure it's not the same cat

        if self.ID == other_cat.ID:
            return False
        
        # no mates check - can be commented out if it's desired to allow MCs to flirt with/date cats regardless of their romantic interactions being limited

        if not ignore_no_mates and (self.no_mates or other_cat.no_mates):
            if self.ID not in other_cat.mate:
                return False
        
        # make sure the cat isn't too closely related

        if self.is_related(other_cat, game.clan.clan_settings["first cousin mates"]):
            return False
        
        # make sure they're not outside the clan or dead

        if self.dead or other_cat.dead or self.outside or other_cat.outside:
            return False
        
        # check age. allow adolescents to flirt with each other. prevent kittens and newborns from flirting

        if age_restriction:
            if (self.moons < 12 or other_cat.moons < 12):
                if self.age in ["adolescent"] or other_cat.age in ["adolescent"]:
                    if self.age != other_cat.age:
                        return False
            if self.age in ["newborn", "kitten"] or other_cat.age in ["newborn", "kitten"]:
                return False
            
            if game.config["mates"].get("override_same_age_group", False) or self.age != other_cat.age:
                if abs(self.moons - other_cat.moons)> game.config["mates"]["age_range"] + 1:
                    if self.ID not in other_cat.mate:
                        return False
        
        # check for mentor

        is_former_mentor = (other_cat.ID in self.former_apprentices or self.ID in other_cat.former_apprentices)
        if is_former_mentor and not game.clan.clan_settings['romantic with former mentor']:
            return False
        if other_cat.ID in self.apprentice or self.ID in other_cat.apprentice:
            return False
        
        return True

    def unset_mate(self, other_cat: Cat, breakup: bool = False, fight: bool = False):
        """Unset the mate from both self and other_cat"""
        if not other_cat:
            return

        # Both cats must have mates for this to work
        if len(self.mate) < 1 or len(other_cat.mate) < 1:
            return

        # AND they must be mates with each other. 
        if self.ID not in other_cat.mate or other_cat.ID not in self.mate:
            print(f"Unsetting mates: These {self.name} and {other_cat.name} are not mates!")
            return

        # If only deal with relationships if this is a breakup. 
        if breakup:
            if not self.dead:
                if other_cat.ID not in self.relationships:
                    self.create_one_relationship(other_cat)
                    self.relationships[other_cat.ID].mate = True
                self_relationship = self.relationships[other_cat.ID]
                self_relationship.romantic_love -= 40
                self_relationship.comfortable -= 20
                self_relationship.trust -= 10
                self_relationship.mate = False
                if fight:
                    self_relationship.platonic_like -= 30
                if randint(1,5) == 1:
                    self.get_ill("heartbroken")
                if randint(1,5) == 1 and not other_cat.dead:
                    other_cat.get_ill("heartbroken")
            if not other_cat.dead:
                if self.ID not in other_cat.relationships:
                    other_cat.create_one_relationship(self)
                    other_cat.relationships[self.ID].mate = True
                other_relationship = other_cat.relationships[self.ID]
                other_relationship.romantic_love -= 40
                other_relationship.comfortable -= 20
                other_relationship.trust -= 10
                other_relationship.mate = False
                if fight:
                    other_relationship.platonic_like -= 30

        self.mate.remove(other_cat.ID)
        other_cat.mate.remove(self.ID)

        # Handle previous mates:
        if other_cat.ID not in self.previous_mates:
            self.previous_mates.append(other_cat.ID)
        if self.ID not in other_cat.previous_mates:
            other_cat.previous_mates.append(self.ID)

        if other_cat.inheritance:
            other_cat.inheritance.update_all_mates()
        if self.inheritance:
            self.inheritance.update_all_mates()

    def set_mate(self, other_cat: Cat):
        """Sets up a mate relationship between self and other_cat."""
        if other_cat.ID not in self.mate:
            self.mate.append(other_cat.ID)
        if self.ID not in other_cat.mate:
            other_cat.mate.append(self.ID)

        # If the current mate was in the previous mate list, remove them. 
        if other_cat.ID in self.previous_mates:
            self.previous_mates.remove(other_cat.ID)
        if self.ID in other_cat.previous_mates:
            other_cat.previous_mates.remove(self.ID)

        if other_cat.inheritance:
            other_cat.inheritance.update_all_mates()
        if self.inheritance:
            self.inheritance.update_all_mates()

        # Set starting relationship values
        if not self.dead:
            if other_cat.ID not in self.relationships:
                self.create_one_relationship(other_cat)
                self.relationships[other_cat.ID].mate =  True
            self_relationship = self.relationships[other_cat.ID]
            self_relationship.romantic_love += 20
            self_relationship.comfortable += 20
            self_relationship.trust += 10
            self_relationship.mate = True

        if not other_cat.dead:
            if self.ID not in other_cat.relationships:
                other_cat.create_one_relationship(self)
                other_cat.relationships[self.ID].mate = True
            other_relationship = other_cat.relationships[self.ID]
            other_relationship.romantic_love += 20
            other_relationship.comfortable += 20
            other_relationship.trust += 10
            other_relationship.mate = True

    def create_inheritance_new_cat(self):
        """Creates the inheritance class for a new cat."""
        # set the born status to true, just for safety
        self.inheritance = Inheritance(self, True)

    def create_one_relationship(self, other_cat: Cat):
        """Create a new relationship between current cat and other cat. Returns: Relationship"""
        if other_cat.ID in self.relationships:
            return self.relationships[other_cat.ID]
        
        if other_cat.ID == self.ID:
            print(f"Attempted to create a relationship with self: {self.name}. Please report as a bug!")
            return None
        
        self.relationships[other_cat.ID] = Relationship(self, other_cat)
        return self.relationships[other_cat.ID]

    def create_relationships_new_cat(self):
        """Create relationships for a new generated cat."""
        for inter_cat in Cat.all_cats.values():
            # the inter_cat is the same as the current cat
            if inter_cat.ID == self.ID:
                continue
            # if the cat already has (somehow) a relationship with the inter cat
            if inter_cat.ID in self.relationships:
                continue
            # if they dead (dead cats have no relationships)
            if self.dead or inter_cat.dead:
                continue
            # if they are not outside of the Clan at the same time
            if self.outside and not inter_cat.outside or not self.outside and inter_cat.outside:
                continue
            inter_cat.relationships[self.ID] = Relationship(inter_cat, self)
            self.relationships[inter_cat.ID] = Relationship(self, inter_cat)


    def init_all_relationships(self):
        """Create Relationships to all current Clancats."""
        for id in self.all_cats:
            the_cat = self.all_cats.get(id)
            if the_cat.ID is not self.ID and the_cat.moons > -1:
                mates = the_cat.ID in self.mate
                are_parents = False
                parents = False
                siblings = False

                if self.parent1 is not None and self.parent2 is not None and \
                        the_cat.parent1 is not None and the_cat.parent2 is not None:
                    are_parents = the_cat.ID in [self.parent1, self.parent2]
                    parents = are_parents or self.ID in [
                        the_cat.parent1, the_cat.parent2
                    ]
                    siblings = self.parent1 in [
                        the_cat.parent1, the_cat.parent2
                    ] or self.parent2 in [the_cat.parent1, the_cat.parent2]

                related = parents or siblings

                # set the different stats
                romantic_love = 0
                like = 0
                dislike = 0
                admiration = 0
                comfortable = 0
                jealousy = 0
                trust = 0
                if game.settings['random relation']:
                    if game.clan:
                        if the_cat == game.clan.instructor or the_cat == game.clan.demon:
                            pass
                        elif randint(1, 20) == 1 and romantic_love < 1:
                            dislike = randint(10, 25)
                            jealousy = randint(5, 15)
                            if randint(1, 30) == 1:
                                trust = randint(1, 10)
                        else:
                            like = randint(0, 35)
                            comfortable = randint(0, 25)
                            trust = randint(0, 15)
                            admiration = randint(0, 20)
                            if randint(
                                    1, 100 - like
                            ) == 1 and self.moons > 11 and the_cat.moons > 11:
                                romantic_love = randint(15, 30)
                                comfortable = int(comfortable * 1.3)
                                trust = int(trust * 1.2)
                    else:
                        if randint(1, 20) == 1 and romantic_love < 1:
                            dislike = randint(10, 25)
                            jealousy = randint(5, 15)
                            if randint(1, 30) == 1:
                                trust = randint(1, 10)
                        else:
                            like = randint(0, 35)
                            comfortable = randint(0, 25)
                            trust = randint(0, 15)
                            admiration = randint(0, 20)
                            if randint(
                                    1, 100 - like
                            ) == 1 and self.moons > 11 and the_cat.moons > 11:
                                romantic_love = randint(15, 30)
                                comfortable = int(comfortable * 1.3)
                                trust = int(trust * 1.2)

                if are_parents and like < 60:
                    like = 60
                if siblings and like < 30:
                    like = 30

                rel = Relationship(cat_from=self,
                                   cat_to=the_cat,
                                   mates=mates,
                                   family=related,
                                   romantic_love=romantic_love,
                                   platonic_like=like,
                                   dislike=dislike,
                                   admiration=admiration,
                                   comfortable=comfortable,
                                   jealousy=jealousy,
                                   trust=trust)
                self.relationships[the_cat.ID] = rel

    def save_relationship_of_cat(self, relationship_dir):
        # save relationships for each cat

        rel = []
        for r in self.relationships.values():
            r_data = {
                "cat_from_id": r.cat_from.ID,
                "cat_to_id": r.cat_to.ID,
                "mates": r.mates,
                "family": r.family,
                "romantic_love": r.romantic_love,
                "platonic_like": r.platonic_like,
                "dislike": r.dislike,
                "admiration": r.admiration,
                "comfortable": r.comfortable,
                "jealousy": r.jealousy,
                "trust": r.trust,
                "log": r.log
            }
            rel.append(r_data)

        game.safe_save(f"{relationship_dir}/{self.ID}_relations.json", rel)

    def load_relationship_of_cat(self):
        if game.switches['clan_name'] != '':
            clanname = game.switches['clan_name']
        else:
            clanname = game.switches['clan_list'][0]

        relation_directory = get_save_dir() + '/' + clanname + '/relationships/'
        relation_cat_directory = relation_directory + self.ID + '_relations.json'

        self.relationships = {}
        if os.path.exists(relation_directory):
            if not os.path.exists(relation_cat_directory):
                self.init_all_relationships()
                for cat in Cat.all_cats.values():
                    cat.create_one_relationship(self)
                return
            try:
                with open(relation_cat_directory, 'r') as read_file:
                    rel_data = ujson.loads(read_file.read())
                    for rel in rel_data:
                        cat_to = self.all_cats.get(rel['cat_to_id'])
                        if cat_to is None or rel['cat_to_id'] == self.ID:
                            continue
                        new_rel = Relationship(
                            cat_from=self,
                            cat_to=cat_to,
                            mates=rel['mates'] if rel['mates'] else False,
                            family=rel['family'] if rel['family'] else False,
                            romantic_love=rel['romantic_love'] if rel['romantic_love'] else 0,
                            platonic_like=rel['platonic_like'] if rel['platonic_like'] else 0,
                            dislike=rel['dislike'] if rel['dislike'] else 0,
                            admiration=rel['admiration'] if rel['admiration'] else 0,
                            comfortable=rel['comfortable'] if rel['comfortable'] else 0,
                            jealousy=rel['jealousy'] if rel['jealousy'] else 0,
                            trust=rel['trust'] if rel['trust'] else 0,
                            log=rel['log'])
                        self.relationships[rel['cat_to_id']] = new_rel
            except:
                print(f'WARNING: There was an error reading the relationship file of cat #{self}.')

    @staticmethod
    def mediate_relationship(mediator, cat1, cat2, allow_romantic, sabotage=False):
        # Gather some important info

        # Gathering the relationships.
        if cat1.ID in cat2.relationships:
            rel1 = cat1.relationships[cat2.ID]
        else:
            rel1 = cat1.create_one_relationship(cat2)

        if cat2.ID in cat1.relationships:
            rel2 = cat2.relationships[cat1.ID]
        else:
            rel2 = cat2.create_one_relationship(cat1)

        # Output string.
        output = ""

        # Determine the chance of failure.
        if mediator.experience_level == "untrained":
            chance = 15
        if mediator.experience_level == "trainee":
            # Negative bonus for very low.
            chance = 20
        elif mediator.experience_level == "prepared":
            chance = 35
        elif mediator.experience_level == "proficient":
            chance = 55
        elif mediator.experience_level == "expert":
            chance = 70
        elif mediator.experience_level == "master":
            chance = 100
        else:
            chance = 40

        compat = get_personality_compatibility(cat1, cat2)
        if compat is True:
            chance += 10
        elif compat is False:
            chance -= 5

        # Cat's compatibility with mediator also has an effect on success chance.
        for cat in [cat1, cat2]:
            if get_personality_compatibility(cat, mediator) is True:
                chance += 5
            elif get_personality_compatibility(cat, mediator) is False:
                chance -= 5

        # Determine chance to fail, turning sabotage into mediate and mediate into sabotage
        if not int(random() * chance):
            apply_bonus = False
            if sabotage:
                output += "Sabotage Failed!\n"
                sabotage = False
            else:
                output += "Mediate Failed!\n"
                sabotage = True
        else:
            apply_bonus = True
            # EX gain on success
            if mediator.status != "mediator apprentice":
                EX_gain = randint(10, 24)

                gm_modifier = 1
                if game.clan and game.clan.game_mode == 'expanded':
                    gm_modifier = 3
                elif game.clan and game.clan.game_mode == 'cruel season':
                    gm_modifier = 6

                if mediator.experience_level == "average":
                    lvl_modifier = 1.25
                elif mediator.experience_level == "high":
                    lvl_modifier = 1.75
                elif mediator.experience_level == "master":
                    lvl_modifier = 2
                else:
                    lvl_modifier = 1
                mediator.experience += EX_gain / lvl_modifier / gm_modifier

        if mediator.status == "mediator apprentice":
            mediator.experience += max(randint(1, 6), 1)

        # determine the traits to effect
        # Are they mates?
        if rel1.cat_from.ID in rel1.cat_to.mate:
            mates = True
        else:
            mates = False
        
        pos_traits = ["platonic", "respect", "comfortable", "trust"]
        if allow_romantic and (mates or cat1.is_potential_mate(cat2)):
            pos_traits.append("romantic")

        neg_traits = ["dislike", "jealousy"]

        # Determine the number of positive traits to effect, and choose the traits
        chosen_pos = sample(pos_traits, k=randint(2, len(pos_traits)))

        # Determine negative trains effected
        neg_traits = sample(neg_traits, k=randint(1, 2))

        if compat is True:
            personality_bonus = 2
        elif compat is False:
            personality_bonus = -2
        else:
            personality_bonus = 0

        # Effects on traits
        for trait in chosen_pos + neg_traits:

            # The EX bonus in not applied upon a fail.
            if apply_bonus:
                if mediator.experience_level == "very low":
                    # Negative bonus for very low.
                    bonus = randint(-2, -1)
                elif mediator.experience_level == "low":
                    bonus = randint(-2, 0)
                elif mediator.experience_level == "high":
                    bonus = randint(1, 3)
                elif mediator.experience_level == "master":
                    bonus = randint(3, 4)
                elif mediator.experience_level == "max":
                    bonus = randint(4, 5)
                else:
                    bonus = 0  # Average gets no bonus.
            else:
                bonus = 0

            if trait == "romantic":
                if mates:
                    ran = (5, 10)
                else:
                    ran = (4, 6)

                if sabotage:
                    rel1.romantic_love = Cat.effect_relation(rel1.romantic_love, -(randint(ran[0], ran[1]) + bonus) +
                                                             personality_bonus)
                    rel2.romantic_love = Cat.effect_relation(rel1.romantic_love, -(randint(ran[0], ran[1]) + bonus) +
                                                             personality_bonus)
                    output += "Romantic interest decreased. "
                else:
                    rel1.romantic_love = Cat.effect_relation(rel1.romantic_love, (randint(ran[0], ran[1]) + bonus) +
                                                             personality_bonus)
                    rel2.romantic_love = Cat.effect_relation(rel2.romantic_love, (randint(ran[0], ran[1]) + bonus) +
                                                             personality_bonus)
                    output += "Romantic interest increased. "

            elif trait == "platonic":
                ran = (4, 6)

                if sabotage:
                    rel1.platonic_like = Cat.effect_relation(rel1.platonic_like, -(randint(ran[0], ran[1]) + bonus) +
                                                             personality_bonus)
                    rel2.platonic_like = Cat.effect_relation(rel2.platonic_like, -(randint(ran[0], ran[1]) + bonus) +
                                                             personality_bonus)
                    output += "Platonic like decreased. "
                else:
                    rel1.platonic_like = Cat.effect_relation(rel1.platonic_like, (randint(ran[0], ran[1]) + bonus) +
                                                             personality_bonus)
                    rel2.platonic_like = Cat.effect_relation(rel2.platonic_like, (randint(ran[0], ran[1]) + bonus) +
                                                             personality_bonus)
                    output += "Platonic like increased. "

            elif trait == "respect":
                ran = (4, 6)

                if sabotage:
                    rel1.admiration = Cat.effect_relation(rel1.admiration, -(randint(ran[0], ran[1]) + bonus) +
                                                          personality_bonus)
                    rel2.admiration = Cat.effect_relation(rel2.admiration, -(randint(ran[0], ran[1]) + bonus) +
                                                          personality_bonus)
                    output += "Respect decreased. "
                else:
                    rel1.admiration = Cat.effect_relation(rel1.admiration, (randint(ran[0], ran[1]) + bonus) +
                                                          personality_bonus)
                    rel2.admiration = Cat.effect_relation(rel2.admiration, (randint(ran[0], ran[1]) + bonus) +
                                                          personality_bonus)
                    output += "Respect increased. "

            elif trait == "comfortable":
                ran = (4, 6)

                if sabotage:
                    rel1.comfortable = Cat.effect_relation(rel1.comfortable, -(randint(ran[0], ran[1]) + bonus) +
                                                           personality_bonus)
                    rel2.comfortable = Cat.effect_relation(rel2.comfortable, -(randint(ran[0], ran[1]) + bonus) +
                                                           personality_bonus)
                    output += "Comfort decreased. "
                else:
                    rel1.comfortable = Cat.effect_relation(rel1.comfortable, (randint(ran[0], ran[1]) + bonus) +
                                                           personality_bonus)
                    rel2.comfortable = Cat.effect_relation(rel2.comfortable, (randint(ran[0], ran[1]) + bonus) +
                                                           personality_bonus)
                    output += "Comfort increased. "

            elif trait == "trust":
                ran = (4, 6)

                if sabotage:
                    rel1.trust = Cat.effect_relation(rel1.trust, -(randint(ran[0], ran[1]) + bonus) +
                                                     personality_bonus)
                    rel2.trust = Cat.effect_relation(rel2.trust, -(randint(ran[0], ran[1]) + bonus) +
                                                     personality_bonus)
                    output += "Trust decreased. "
                else:
                    rel1.trust = Cat.effect_relation(rel1.trust, (randint(ran[0], ran[1]) + bonus) +
                                                     personality_bonus)
                    rel2.trust = Cat.effect_relation(rel2.trust, (randint(ran[0], ran[1]) + bonus) +
                                                     personality_bonus)
                    output += "Trust increased. "

            elif trait == "dislike":
                ran = (4, 9)
                if sabotage:
                    rel1.dislike = Cat.effect_relation(rel1.dislike, (randint(ran[0], ran[1]) + bonus) -
                                                       personality_bonus)
                    rel2.dislike = Cat.effect_relation(rel2.dislike, (randint(ran[0], ran[1]) + bonus) -
                                                       personality_bonus)
                    output += "Dislike increased. "
                else:
                    rel1.dislike = Cat.effect_relation(rel1.dislike, -(randint(ran[0], ran[1]) + bonus) -
                                                       personality_bonus)
                    rel2.dislike = Cat.effect_relation(rel2.dislike, -(randint(ran[0], ran[1]) + bonus) -
                                                       personality_bonus)
                    output += "Dislike decreased. "

            elif trait == "jealousy":
                ran = (4, 6)

                if sabotage:
                    rel1.jealousy = Cat.effect_relation(rel1.jealousy, (randint(ran[0], ran[1]) + bonus) -
                                                        personality_bonus)
                    rel2.jealousy = Cat.effect_relation(rel2.jealousy, (randint(ran[0], ran[1]) + bonus) -
                                                        personality_bonus)
                    output += "Jealousy increased. "
                else:
                    rel1.jealousy = Cat.effect_relation(rel1.jealousy, -(randint(ran[0], ran[1]) + bonus) -
                                                        personality_bonus)
                    rel2.jealousy = Cat.effect_relation(rel2.jealousy, -(randint(ran[0], ran[1]) + bonus) -
                                                        personality_bonus)
                    output += "Jealousy decreased . "

        return output

    @staticmethod
    def effect_relation(current_value, effect):
        if effect < 0:
            if abs(effect) >= current_value:
                return 0

        if effect > 0:
            if current_value + effect >= 100:
                return 100

        return current_value + effect

    def set_faded(self):
        """This function is for cats that are faded. It will set the sprite and the faded tag"""
        self.faded = True

        # Silhouette sprite
        if self.age == 'newborn':
            file_name = "faded_newborn"
        elif self.age == 'kitten':
            file_name = "faded_kitten"
        elif self.age in ['adult', 'young adult', 'senior adult']:
            file_name = "faded_adult"
        elif self.age == "adolescent":
            file_name = "faded_adol"
        else:
            file_name = "faded_senior"

        if self.df:
            file_name += "_df"

        file_name += ".png"

        self.sprite = image_cache.load_image(f"sprites/faded/{file_name}").convert_alpha()

    @staticmethod
    def fetch_cat(cat_id: str):
        """Fetches a cat object. Works for both faded and non-faded cats. Returns none if no cat was found. """
        if not cat_id or isinstance(cat_id, Cat):  # Check if argument is None or Cat.
            return cat_id
        elif not isinstance(cat_id, str):  # Invalid type
            return None
        if cat_id in Cat.all_cats:
            return Cat.all_cats[cat_id]
        else:
            ob = Cat.load_faded_cat(cat_id)
            if ob:
                return ob
            else:
                return None

    @staticmethod
    def load_faded_cat(cat: str):
        """Loads a faded cat, returning the cat object. This object is saved nowhere else. """
        try:
            with open(get_save_dir() + '/' + game.clan.name + '/faded_cats/' + cat + ".json", 'r') as read_file:
                cat_info = ujson.loads(read_file.read())
        except AttributeError:  # If loading cats is attempted before the Clan is loaded, we would need to use this.
            with open(get_save_dir() + '/' + game.switches['clan_list'][0] + '/faded_cats/' + cat + ".json",
                      'r') as read_file:
                cat_info = ujson.loads(read_file.read())
        except Exception as e:
            print(e)
            print("ERROR: in loading faded cat")
            return False

        cat_ob = Cat(ID=cat_info["ID"], prefix=cat_info["name_prefix"], suffix=cat_info["name_suffix"],
                     status=cat_info["status"], moons=cat_info["moons"], faded=True,
                     df=cat_info["df"] if "df" in cat_info else False)
        if cat_info["parent1"]:
            cat_ob.parent1 = cat_info["parent1"]
        if cat_info["parent2"]:
            cat_ob.parent2 = cat_info["parent2"]
        cat_ob.faded_offspring = cat_info["faded_offspring"]
        cat_ob.adoptive_parents = cat_info["adoptive_parents"] if "adoptive_parents" in cat_info else []
        cat_ob.faded = True
        cat_ob.dead_for = cat_info["dead_for"] if "dead_for" in cat_info else 1

        return cat_ob

    # ---------------------------------------------------------------------------- #
    #                                  Sorting                                     #
    # ---------------------------------------------------------------------------- #

    @staticmethod
    def sort_cats(given_list=[]):
        if not given_list:
            given_list = Cat.all_cats_list
        if game.sort_type == "age":
            given_list.sort(key=lambda x: Cat.get_adjusted_age(x))
        elif game.sort_type == "reverse_age":
            given_list.sort(key=lambda x: Cat.get_adjusted_age(x), reverse=True)
        elif game.sort_type == "id":
            given_list.sort(key=lambda x: int(x.ID))
        elif game.sort_type == "reverse_id":
            given_list.sort(key=lambda x: int(x.ID), reverse=True)
        elif game.sort_type == "rank":
            given_list.sort(key=lambda x: (Cat.rank_order(x), Cat.get_adjusted_age(x)), reverse=True)
        elif game.sort_type == "exp":
            given_list.sort(key=lambda x: x.experience, reverse=True)
        elif game.sort_type == "death":
            given_list.sort(key=lambda x: -1 * int(x.dead_for))

        return

    @staticmethod
    def insert_cat(c: Cat):
        try:
            if game.sort_type == "age":
                bisect.insort(Cat.all_cats_list, c, key=lambda x: Cat.get_adjusted_age(x))
            elif game.sort_type == "reverse_age":
                bisect.insort(Cat.all_cats_list, c, key=lambda x: -1 * Cat.get_adjusted_age(x))
            elif game.sort_type == "rank":
                bisect.insort(Cat.all_cats_list, c, key=lambda x: (-1 * Cat.rank_order(x), -1 *
                                                                   Cat.get_adjusted_age(x)))
            elif game.sort_type == "exp":
                bisect.insort(Cat.all_cats_list, c, key=lambda x: x.experience)
            elif game.sort_type == "id":
                bisect.insort(Cat.all_cats_list, c, key=lambda x: int(x.ID))
            elif game.sort_type == "reverse_id":
                bisect.insort(Cat.all_cats_list, c, key=lambda x: -1 * int(x.ID))
            elif game.sort_type == "death":
                bisect.insort(Cat.all_cats_list, c, key=lambda x: -1 * int(x.dead_for))
        except (TypeError, NameError):
            # If you are using python 3.8, key is not a supported parameter into insort. Therefore, we'll need to
            # do the slower option of adding the cat, then resorting
            Cat.all_cats_list.append(c)
            Cat.sort_cats()

    @staticmethod
    def rank_order(cat: Cat):
        if cat.status in Cat.rank_sort_order and cat.shunned == 0:
            return Cat.rank_sort_order.index(cat.status)
        else:
            return 0

    @staticmethod
    def get_adjusted_age(cat: Cat):
        """Returns the moons + dead_for moons rather than the moons at death for dead cats, so dead cats are sorted by
        total age, rather than age at death"""
        if cat.dead:
            if game.config["sorting"]["sort_rank_by_death"]:
                if game.sort_type == "rank":
                    return cat.dead_for
                else:
                    if game.config["sorting"]["sort_dead_by_total_age"]:
                        return cat.dead_for + cat.moons
                    else:
                        return cat.moons
            else:
                if game.config["sorting"]["sort_dead_by_total_age"]:
                    return cat.dead_for + cat.moons
                else:
                    return cat.moons
        else:
            return cat.moons
        
    # ---------------------------------------------------------------------------- #
    #                                  properties                                  #
    # ---------------------------------------------------------------------------- #

    @property
    def experience(self):
        return self._experience

    @experience.setter
    def experience(self, exp: int):
        if exp > self.experience_levels_range["master"][1]:
            exp = self.experience_levels_range["master"][1]
        self._experience = int(exp)

        for x in self.experience_levels_range:
            if self.experience_levels_range[x][0] <= exp <= self.experience_levels_range[x][1]:
                self.experience_level = x
                break

    @property
    def moons(self):
        return self._moons

    @moons.setter
    def moons(self, value: int):
        self._moons = value
        
        updated_age = False
        for key_age in self.age_moons.keys():
            if self._moons in range(self.age_moons[key_age][0], self.age_moons[key_age][1] + 1):
                updated_age = True
                self.age = key_age
        try:
            if self.moons == -1:
                self.age = "newborn"
            elif not updated_age and self.age is not None:
                self.age = "senior"
        except AttributeError:
            print("ERROR: cat has no age attribute! Cat ID: " + self.ID)
        
    @property
    def sprite(self):
        # Update the sprite
        update_sprite(self)
        return self._sprite

    @sprite.setter
    def sprite(self, new_sprite):
        self._sprite = new_sprite
        
    # ---------------------------------------------------------------------------- #
    #                                  other                                       #
    # ---------------------------------------------------------------------------- #
    
    def is_baby(self):
        return self.age in ["kitten", "newborn"]
    
    def get_save_dict(self, faded=False):
        if faded:
            return {
                "ID": self.ID,
                "name_prefix": self.name.prefix,
                "name_suffix": self.name.suffix,
                "status": self.status,
                "moons": self.moons,
                "dead_for": self.dead_for,
                "parent1": self.parent1,
                "parent2": self.parent2,
                "adoptive_parents": self.adoptive_parents,
                "df": self.df,
                "faded_offspring": self.faded_offspring
            }
        else:
            return {
                "ID": self.ID,
                "name_prefix": self.name.prefix,
                "name_suffix": self.name.suffix,
                "specsuffix_hidden": self.name.specsuffix_hidden,
                "gender": self.gender,
                "gender_align": self.genderalign,
                #"pronouns": self.pronouns,
                "birth_cooldown": self.birth_cooldown,
                "status": self.status,
                "backstory": self.backstory if self.backstory else None,
                "moons": self.moons,
                "trait": self.personality.trait,
                "facets": self.personality.get_facet_string(),
                "parent1": self.parent1,
                "parent2": self.parent2,
                "adoptive_parents": self.adoptive_parents,
                "mentor": self.mentor if self.mentor else None,
                "former_mentor": [cat for cat in self.former_mentor] if self.former_mentor else [],
                "patrol_with_mentor": self.patrol_with_mentor if self.patrol_with_mentor else 0,
                "mate": self.mate,
                "previous_mates": self.previous_mates,
                "dead": self.dead,
                "paralyzed": self.pelt.paralyzed,
                "no_kits": self.no_kits,
                "exiled": self.exiled,
                "genotype": self.genotype.toJSON(),
                "white_pattern" : self.genotype.white_pattern,
                "chim_white" : self.genotype.chimerageno.white_pattern if self.genotype.chimerageno else "No",
                "no_retire": self.no_retire,
                "no_mates": self.no_mates,
                "sprite_kitten": self.pelt.cat_sprites['kitten'],
                "sprite_adolescent": self.pelt.cat_sprites['adolescent'],
                "sprite_adult": self.pelt.cat_sprites['adult'],
                "sprite_senior": self.pelt.cat_sprites['senior'],
                "sprite_para_adult": self.pelt.cat_sprites['para_adult'],
                "reverse": self.pelt.reverse,
                "accessories": self.pelt.accessories if self.pelt.accessories else [],
                # "skin": self.pelt.skin,
                # "tint": self.pelt.tint,
                "skill_dict": self.skills.get_skill_dict(),
                "scars": self.pelt.scars if self.pelt.scars else [],
                "accessory": self.pelt.accessory,
                "experience": self.experience,
                "dead_moons": self.dead_for,
                "shunned": self.shunned,
                "current_apprentice": [appr for appr in self.apprentice],
                "former_apprentices": [appr for appr in self.former_apprentices],
                "df": self.df,
                "outside": self.outside,
                "faded_offspring": self.faded_offspring,
                "opacity": self.pelt.opacity,
                "prevent_fading": self.prevent_fading,
                "favourite": self.favourite,
                "w_done": self.w_done if self.w_done else False,
                "talked_to": self.talked_to if self.talked_to else False,
                "insulted": self.insulted if self.insulted else False,
                "flirted": self.flirted if self.flirted else False,
                "joined_df": self.joined_df if self.joined_df else False,
                "forgiven": self.forgiven if self.forgiven and isinstance(self.forgiven, int) else 0,
                "inventory": self.pelt.inventory if self.pelt.inventory else [],
                "revives": self.revives if self.revives else 0,
                "backstory_str": self.backstory_str if self.backstory_str else "",
                "courage": self.courage if self.courage else 0,
                "compassion": self.compassion if self.compassion else 0,
                "intelligence": self.intelligence if self.intelligence else 0,
                "empathy": self.empathy if self.empathy else 0,
                "did_activity": self.did_activity if self.did_activity else False,
                "df_mentor": self.df_mentor if self.df_mentor else None,
                "df_apprentices": self.df_apprentices if self.df_apprentices else []
            }


        
# ---------------------------------------------------------------------------- #
#                               END OF CAT CLASS                               #
# ---------------------------------------------------------------------------- #

# ---------------------------------------------------------------------------- #
#                               PERSONALITY CLASS                              #
# ---------------------------------------------------------------------------- #

class Personality():
    """Hold personality information for a cat, and functions to deal with it """
    facet_types = ["lawfulness", "sociability", "aggression", "stability"]
    facet_range = [0, 15]
    
    with open("resources/dicts/traits/trait_ranges.json", "r") as read_file:
        trait_ranges = ujson.loads(read_file.read())
    
    def __init__(self, trait:str=None, kit_trait:bool=False, lawful:int=None, social:int=None, aggress:int=None, 
                 stable:int=None) -> Personality:
        """If trait is given, it will randomize facets within the range of the trait. It will ignore any facets given. 
            If facets are given and no trait, it will find a trait that matches the facets. NOTE: you can give
            only some facets: It will randomize any you don't specify.
            If both facets and trait are given, it will use the trait if it matched the facets. Otherwise it will
            find a new trait."""
        self._law = 0
        self._social = 0
        self._aggress = 0
        self._stable = 0
        self.trait = None
        self.kit = kit_trait #If true, use kit trait. If False, use normal traits. 
        
        if self.kit:
            trait_type_dict = Personality.trait_ranges["kit_traits"]
        else:
            trait_type_dict = Personality.trait_ranges["normal_traits"]
        
        _tr = None
        if trait and trait in trait_type_dict:
            # Trait-given init
            self.trait = trait
            _tr = trait_type_dict[self.trait]
        
        # Set Facet Values
        # The priority of is: 
        # (1) Given value, from parameter. 
        # (2) If a trait range is assigned, pick from trait range
        # (3) Totally random. 
        if lawful is not None:
            self._law = Personality.adjust_to_range(lawful)
        elif _tr:
            self._law = randint(_tr["lawfulness"][0], _tr["lawfulness"][1])
        else:
            self._law = randint(Personality.facet_range[0], Personality.facet_range[1])
            
        if social is not None:
            self._social = Personality.adjust_to_range(social)
        elif _tr:
            self._social = randint(_tr["sociability"][0], _tr["sociability"][1])
        else:
            self._social = randint(Personality.facet_range[0], Personality.facet_range[1])
            
        if aggress is not None:
            self._aggress = Personality.adjust_to_range(aggress)
        elif _tr:
            self._aggress = randint(_tr["aggression"][0], _tr["aggression"][1])
        else:
            self._aggress = randint(Personality.facet_range[0], Personality.facet_range[1])
            
        if stable is not None:
            self._stable = Personality.adjust_to_range(stable)
        elif _tr:
            self._stable = randint(_tr["stability"][0], _tr["stability"][1])
        else:
            self._stable = randint(Personality.facet_range[0], Personality.facet_range[1])
                
        # If trait is still empty, or if the trait is not valid with the facets, change it. 
        if not self.trait or not self.is_trait_valid():
            self.choose_trait()
                
    def __repr__(self) -> str:
        """For debugging"""
        return f"{self.trait}: lawfulness {self.lawfulness}, aggression {self.aggression}, sociability {self.sociability}, stablity {self.stability}"
    
    def get_facet_string(self):
        """For saving the facets to file."""
        return f"{self.lawfulness},{self.sociability},{self.aggression},{self.stability}"
    
    def __getitem__(self, key):
        """Alongside __setitem__, Allows you to treat this like a dictionary if you want. """
        return getattr(self, key)
    
    def __setitem__(self, key, newval):
        """Alongside __getitem__, Allows you to treat this like a dictionary if you want. """
        setattr(self, key, newval)

    # ---------------------------------------------------------------------------- #
    #                               PROPERTIES                                     #
    # ---------------------------------------------------------------------------- #
    
    @property
    def lawfulness(self):
        return self._law
    
    @lawfulness.setter
    def lawfulness(self, new_val):
        """Do not use property in init"""
        self._law = Personality.adjust_to_range(new_val)
        if not self.is_trait_valid():
            self.choose_trait()
            
    @property
    def sociability(self):
        return self._social
    
    @sociability.setter
    def sociability(self, new_val):
        """Do not use property in init"""
        self._social = Personality.adjust_to_range(new_val)
        if not self.is_trait_valid():
            self.choose_trait()
            
    @property
    def aggression(self):
        return self._aggress
    
    @aggression.setter
    def aggression(self, new_val):
        """Do not use property in init"""
        self._aggress = Personality.adjust_to_range(new_val)
        if not self.is_trait_valid():
            self.choose_trait()
            
    @property
    def stability(self):
        return self._stable
    
    @stability.setter
    def stability(self, new_val):
        """Do not use property in init"""
        self._stable = Personality.adjust_to_range(new_val)
        if not self.is_trait_valid():
            self.choose_trait()
            

    # ---------------------------------------------------------------------------- #
    #                               METHODS                                        #
    # ---------------------------------------------------------------------------- #

    @staticmethod
    def adjust_to_range(val:int) -> int:
        """Take an integer and adjust it to be in the trait-range """
        
        if val < Personality.facet_range[0]:
            val = Personality.facet_range[0]
        elif val > Personality.facet_range[1]:
            val = Personality.facet_range[1]
        
        return val
    
    def set_kit(self, kit:bool):
        """Switch the trait-type. True for kit, False for normal"""
        self.kit = kit
        if not self.is_trait_valid():
            self.choose_trait()
        
    def is_trait_valid(self) -> bool:
        """Return True if the current facets fit the trait ranges, false
        if it doesn't. Also returns false if the trait is not in the trait dict.  """
        
        if self.kit:
            trait_type_dict = Personality.trait_ranges["kit_traits"]
        else:
            trait_type_dict = Personality.trait_ranges["normal_traits"]
        
        if self.trait not in trait_type_dict:
            return False
        
        trait_range = trait_type_dict[self.trait]
        
        if not (trait_range["lawfulness"][0] <= self.lawfulness 
                <= trait_range["lawfulness"][1]):
            return False
        if not (trait_range["sociability"][0] <= self.sociability 
                <= trait_range["sociability"][1]):
            return False
        if not (trait_range["aggression"][0] <= self.aggression 
                <= trait_range["aggression"][1]):
            return False
        if not (trait_range["stability"][0] <= self.stability 
                <= trait_range["stability"][1]):
            return False
        
        return True
    
    def choose_trait(self):
        """Chooses trait based on the facets """
        
        if self.kit:
            trait_type_dict = Personality.trait_ranges["kit_traits"]
        else:
            trait_type_dict = Personality.trait_ranges["normal_traits"]
        
        possible_traits = []
        for trait, fac in trait_type_dict.items():
            if not (fac["lawfulness"][0] <= self.lawfulness <= fac["lawfulness"][1]):
                continue
            if not (fac["sociability"][0] <= self.sociability <= fac["sociability"][1]):
                continue
            if not (fac["aggression"][0] <= self.aggression <= fac["aggression"][1]):
                continue
            if not (fac["stability"][0] <= self.stability <= fac["stability"][1]):
                continue
            
            possible_traits.append(trait)
            
        if possible_traits:
            self.trait = choice(possible_traits)
        else:
            print("No possible traits! Using 'strange'")
            self.trait = "strange"
            
    def facet_wobble(self, max=5):
        """Makes a small adjustment to all the facets, and redetermines trait if needed."""        
        self.lawfulness += randint(-max, max)
        self.stability += randint(-max, max)
        self.aggression += randint(-max, max)
        self.sociability += randint(-max, max)
        
    def mentor_influence(self, mentor:Cat):
        """applies mentor influence after the pair go on a patrol together 
            returns history information in the form (mentor_id, facet_affected, amount_affected)"""
        mentor_personality = mentor.personality
        
        #Get possible facet values
        possible_facets = {i: mentor_personality[i] - self[i] for i in 
                           Personality.facet_types if mentor_personality[i] - self[i] != 0}
        
        if possible_facets:
            # Choice trait to effect, weighted by the abs of the difference (higher difference = more likely to effect)
            facet_affected = choices([i for i in possible_facets], weights=[abs(i) for i in possible_facets.values()], k=1)[0]
            # stupid python with no sign() function by default. 
            amount_affected = int(possible_facets[facet_affected]/abs(possible_facets[facet_affected]) * randint(1, 2))
            self[facet_affected] += amount_affected
            return (mentor.ID, facet_affected, amount_affected)
        else:
            #This will only trigger if they have the same personality. 
            return None

# Twelve example cats
def create_example_cats():
    e = sample(range(12), 3)
    not_allowed = ['NOPAW', 'NOTAIL', 'HALFTAIL', 'NOEAR', 'BOTHBLIND', 'RIGHTBLIND', 'LEFTBLIND', 'BRIGHTHEART',
                   'NOLEFTEAR', 'NORIGHTEAR', 'MANLEG']
    for a in range(12):
        if a in e:
            game.choose_cats[a] = Cat(status='kitten', biome=None)
        else:
            game.choose_cats[a] = Cat(status=choice(
                ['kitten']), biome=None)
        if game.choose_cats[a].moons >= 160:
            game.choose_cats[a].moons = choice(range(120, 155))
        elif game.choose_cats[a].moons == 0:
            game.choose_cats[a].moons = choice([1, 2, 3, 4, 5])
        for scar in game.choose_cats[a].pelt.scars:
            if scar in not_allowed:
                game.choose_cats[a].pelt.scars.remove(scar)
            
        chance = game.config["cat_generation"]["base_permanent_condition"]
        if not int(random() * chance):
            possible_conditions = []
            for condition in PERMANENT:
                if PERMANENT[condition]['congenital'] not in ['always', 'sometimes']:
                    continue
                # next part ensures that a kit won't get a condition that takes too long to reveal
                age = game.choose_cats[a].moons
                leeway = 5 - (PERMANENT[condition]['moons_until'] + 1)
                if age > leeway:
                    continue
                possible_conditions.append(condition)
                
            if possible_conditions:
                chosen_condition = choice(possible_conditions)
                born_with = False
                if PERMANENT[chosen_condition]['congenital'] in ['always', 'sometimes']:
                    born_with = True

                game.choose_cats[a].get_permanent_condition(chosen_condition, born_with)
                if game.choose_cats[a].permanent_condition[chosen_condition]["moons_until"] == 0:
                    game.choose_cats[a].permanent_condition[chosen_condition]["moons_until"] = -2

                # assign scars
                if chosen_condition in ['lost a leg', 'born without a leg']:
                    game.choose_cats[a].pelt.scars.append('NOPAW')
                elif chosen_condition in ['lost their tail', 'born without a tail']:
                    game.choose_cats[a].pelt.scars.append("NOTAIL")
        #update_sprite(game.choose_cats[a])
    

# CAT CLASS ITEMS
cat_class = Cat(example=True)
game.cat_class = cat_class

# ---------------------------------------------------------------------------- #
#                                load json files                               #
# ---------------------------------------------------------------------------- #

resource_directory = "resources/dicts/conditions/"

with open(f"{resource_directory}illnesses.json", 'r') as read_file:
    ILLNESSES = ujson.loads(read_file.read())

with open(f"{resource_directory}injuries.json", 'r') as read_file:
    INJURIES = ujson.loads(read_file.read())

with open(f"{resource_directory}permanent_conditions.json", 'r') as read_file:
    PERMANENT = ujson.loads(read_file.read())

resource_directory = "resources/dicts/events/death/death_reactions/"

with open(f"{resource_directory}minor_major.json", 'r') as read_file:
    MINOR_MAJOR_REACTION = ujson.loads(read_file.read())

with open(f"resources/dicts/lead_ceremony_sc.json", 'r') as read_file:
    LEAD_CEREMONY_SC = ujson.loads(read_file.read())

with open(f"resources/dicts/lead_ceremony_df.json", 'r') as read_file:
    LEAD_CEREMONY_DF = ujson.loads(read_file.read())

with open(f"resources/dicts/backstories.json", 'r') as read_file:
    BACKSTORIES = ujson.loads(read_file.read())
