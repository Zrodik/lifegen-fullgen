from scripts.cat.names import names
from scripts.cat_relations.relationship import Relationship
from scripts.cat.genotype import Genotype

import random

from scripts.cat.cats import Cat, INJURIES, BACKSTORIES
from scripts.events_module.generate_events import GenerateEvents
from scripts.utility import event_text_adjust, change_clan_relations, change_relationship_values, create_new_cat
from scripts.game_structure.game_essentials import game
from scripts.event_class import Single_Event
from scripts.cat.names import Name
from scripts.cat.history import History

# pylint: disable=f-string-without-interpolation

# ---------------------------------------------------------------------------- #
#                               New Cat Event Class                              #
# ---------------------------------------------------------------------------- #

class NewCatEvents:
    """All events with a connection to new cats."""

    @staticmethod
    def handle_new_cats(cat: Cat, other_cat, war, enemy_clan, alive_kits):
        """ 
        This function handles the new cats
        """
        if war:
            other_clan = enemy_clan
        else:
            other_clan = random.choice(game.clan.all_clans)
        other_clan_name = f'{other_clan.name}Clan'

        if other_clan_name == 'None':
            other_clan = game.clan.all_clans[0]
            other_clan_name = f'{other_clan.name}Clan'

        #Determine
        if NewCatEvents.has_outside_cat():
            if random.randint(1, 3) == 1:
                outside_cat = NewCatEvents.select_outside_cat()
                backstory = outside_cat.status
                outside_cat = NewCatEvents.update_cat_properties(outside_cat)

                if outside_cat.shunned >= 1:
                    event_text = f"A patrol finds {outside_cat.name} on the border, where they ask to be let into the Clan."
                    allowchance = random.randint(1,2)
                    if allowchance == 1:
                        event_text = event_text + f" After some deliberation, they are accepted."
                    else:
                        event_text = event_text + f" The patrol sends them off with a reminder of why they had to leave to begin with."
                        return
                else:
                    event_text = f"A {backstory} named {outside_cat.name} waits on the border, asking to join the Clan."
                name_change = random.choice([1, 2])

                if outside_cat.shunned == 0:
                    if name_change == 1 or backstory == 'former Clancat':
                        event_text = event_text + f" They decide to keep their name."
                    elif name_change == 2 and backstory != 'former Clancat':
                        outside_cat.name = Name(outside_cat.status,
                                                colour=outside_cat.pelt.colour,
                                                eyes=outside_cat.pelt.eye_colour,
                                                pelt=outside_cat.pelt.name,
                                                tortiepattern=outside_cat.pelt.tortiepattern,
                                                biome=game.clan.biome)
                        
                        event_text = event_text + f" They decide to take a new name, {outside_cat.name}."
                if outside_cat.shunned == 0:
                    outside_cat.thought = "Is looking around the camp with wonder"
                else:
                    outside_cat.thought = "Is glad to be back, despite everything"
                    outside_cat.shunned = 0
                involved_cats = [outside_cat.ID]
                game.cur_events_list.append(Single_Event(event_text, ["misc"], involved_cats))

                # add them 
                for the_cat in outside_cat.all_cats.values():
                    if the_cat.dead or the_cat.outside or the_cat.ID == outside_cat.ID:
                        continue
                    the_cat.create_one_relationship(outside_cat)
                    outside_cat.create_one_relationship(the_cat)

                # takes cat out of the outside cat list
                game.clan.add_to_clan(outside_cat)
                history = History()
                history.add_beginning(outside_cat)

                return [outside_cat]

        
        # ---------------------------------------------------------------------------- #
        #                                cat creation                                  #
        # ---------------------------------------------------------------------------- #
        possible_events = GenerateEvents.possible_short_events(cat.status, cat.age, "new_cat")
        final_events = GenerateEvents.filter_possible_short_events(possible_events, cat, other_cat, war,
                                                                        enemy_clan,
                                                                        other_clan, alive_kits)
        if not final_events:
            print('ERROR: no new cat moon events available')
            return
        else:
            new_cat_event = (random.choice(final_events))

        involved_cats = []
        created_cats = []
        if "m_c" in new_cat_event.tags:
            involved_cats = [cat.ID]

        if "other_cat" in new_cat_event.tags:
            involved_cats = [other_cat.ID]
        else:
            other_cat = None

        status = None
        if "new_warrior" in new_cat_event.tags:
            status = "warrior"
        elif "new_app" in new_cat_event.tags:
            status = "apprentice"
        elif "new_med_app" in new_cat_event.tags:
            status = "medicine cat apprentice"
        elif "new_med" in new_cat_event.tags:
            status = "medicine cat"

        cat_type = ""
        blood_parent = None
        blood_parent2 = None
        par2geno = None
        if new_cat_event.litter or new_cat_event.kit:
            # If we have a litter joining, assign them a blood parent for
            # relation-tracking purposes
            thought = "Is happy their kits are safe"
            ages = [random.randint(15,120), 0]
            ages[1] = ages[0] + random.randint(0, 24) - 12
            
            if('rogue' in new_cat_event.event_text):
                cat_type = 'rogue'
            elif('loner' in new_cat_event.event_text):
                cat_type = 'loner'
            elif('kittypet' in new_cat_event.event_text):
                cat_type = 'kittypet'
            else:
                cat_type = 'del'
            
            blood_parent = create_new_cat(Cat, Relationship,
                                          status=random.choice(["loner", "rogue", "kittypet"]),
                                          alive=True,
                                          thought=thought,
                                          age=ages[0],
                                          gender='masc',
                                          outside=True)[0]
            while 'infertility' in blood_parent.permanent_condition:
                blood_parent = create_new_cat(Cat, Relationship,
                                          status=random.choice(["loner", "rogue", "kittypet"]),
                                          alive=True,
                                          thought=thought,
                                          age=ages[0],
                                          gender='masc',
                                          outside=True)[0]
            if cat_type != 'del':
                blood_parent2 = create_new_cat(Cat, Relationship,
                                          status=cat_type if cat_type != 'del' else 'rogue',
                                          alive=True,
                                          thought=thought,
                                          age=ages[1] if ages[1] > 14 else 15,
                                          gender='fem',
                                          outside=True)[0]
                while 'infertility' in blood_parent2.permanent_condition:
                    blood_parent = create_new_cat(Cat, Relationship,
                                            status=random.choice(["loner", "rogue", "kittypet"]),
                                            alive=True,
                                            thought=thought,
                                            age=ages[0],
                                            gender='masc',
                                            outside=True)[0]
            else:
                par2geno = Genotype(game.config['genetic_chances'])
                par2geno.Generator('fem')

        created_cats = create_new_cat(Cat,
                                      Relationship,
                                      new_cat_event.new_name,
                                      new_cat_event.loner,
                                      new_cat_event.kittypet,
                                      new_cat_event.kit,
                                      new_cat_event.litter,
                                      new_cat_event.other_clan,
                                      new_cat_event.backstory,
                                      status,
                                      parent1=blood_parent2.ID if blood_parent2 else None,
                                      parent2=blood_parent.ID if blood_parent else None,
                                      extrapar = par2geno
                                      )
            
            
        for new_cat in created_cats:
            
            involved_cats.append(new_cat.ID)
            
            # Set the blood parent, if one was created.
            # Also set adoptive parents if needed. 
            if "adoption" in new_cat_event.tags and cat.ID not in new_cat.adoptive_parents:
                new_cat.adoptive_parents.append(cat.ID)
                if len(cat.mate) > 0:
                    for mate_id in cat.mate:
                        if mate_id not in new_cat.adoptive_parents:
                            new_cat.adoptive_parents.extend(cat.mate)
            
            # All parents have been added now, we now create the inheritance. 
            new_cat.create_inheritance_new_cat()

            if "m_c" in new_cat_event.tags:
                # print('moon event new cat rel gain')
                cat.create_one_relationship(new_cat)
                new_cat.create_one_relationship(cat)
                
                new_to_clan_cat = game.config["new_cat"]["rel_buff"]["new_to_clan_cat"]
                clan_cat_to_new = game.config["new_cat"]["rel_buff"]["clan_cat_to_new"]
                change_relationship_values(
                    cats_to=[cat.ID],
                    cats_from=[new_cat],
                    romantic_love=new_to_clan_cat["romantic"],
                    platonic_like=new_to_clan_cat["platonic"],
                    dislike=new_to_clan_cat["dislike"],
                    admiration=new_to_clan_cat["admiration"],
                    comfortable=new_to_clan_cat["comfortable"],
                    jealousy=new_to_clan_cat["jealousy"],
                    trust=new_to_clan_cat["trust"]
                )
                change_relationship_values(
                    cats_to=[new_cat.ID],
                    cats_from=[cat],
                    romantic_love=clan_cat_to_new["romantic"],
                    platonic_like=clan_cat_to_new["platonic"],
                    dislike=clan_cat_to_new["dislike"],
                    admiration=clan_cat_to_new["admiration"],
                    comfortable=clan_cat_to_new["comfortable"],
                    jealousy=clan_cat_to_new["jealousy"],
                    trust=clan_cat_to_new["trust"]
                )

        if "adoption" in new_cat_event.tags:
            if new_cat_event.litter:
                for new_cat in created_cats:
                    # giving relationships for siblings
                    siblings = new_cat.get_siblings()
                    for sibling in siblings:
                        sibling = Cat.fetch_cat(sibling)
                        
                        sibling.create_one_relationship(new_cat)
                        new_cat.create_one_relationship(sibling)
                        
                        cat1_to_cat2 = game.config["new_cat"]["sib_buff"]["cat1_to_cat2"]
                        cat2_to_cat1 = game.config["new_cat"]["sib_buff"]["cat2_to_cat1"]
                        change_relationship_values(
                            cats_to=[sibling.ID],
                            cats_from=[new_cat],
                            romantic_love=cat1_to_cat2["romantic"],
                            platonic_like=cat1_to_cat2["platonic"],
                            dislike=cat1_to_cat2["dislike"],
                            admiration=cat1_to_cat2["admiration"],
                            comfortable=cat1_to_cat2["comfortable"],
                            jealousy=cat1_to_cat2["jealousy"],
                            trust=cat1_to_cat2["trust"]
                        )
                        change_relationship_values(
                            cats_to=[new_cat.ID],
                            cats_from=[sibling],
                            romantic_love=cat2_to_cat1["romantic"],
                            platonic_like=cat2_to_cat1["platonic"],
                            dislike=cat2_to_cat1["dislike"],
                            admiration=cat2_to_cat1["admiration"],
                            comfortable=cat2_to_cat1["comfortable"],
                            jealousy=cat2_to_cat1["jealousy"],
                            trust=cat2_to_cat1["trust"]
                        )

        # give injuries to other cat if tagged as such
        if "injured" in new_cat_event.tags and game.clan.game_mode != "classic":
            major_injuries = []
            if "major_injury" in new_cat_event.tags:
                for injury in INJURIES:
                    if INJURIES[injury]["severity"] == "major" and injury not in ["pregnant", "recovering from birth"]:
                        major_injuries.append(injury)
            for new_cat in created_cats:
                for tag in new_cat_event.tags:
                    if tag in INJURIES:
                        new_cat.get_injured(tag)
                    elif tag == "major_injury":
                        injury = random.choice(major_injuries)
                        new_cat.get_injured(injury)

        if "rel_down" in new_cat_event.tags:
            difference = -1
            change_clan_relations(other_clan, difference=difference)

        elif "rel_up" in new_cat_event.tags:
            difference = 1
            change_clan_relations(other_clan, difference=difference)

        event_text = event_text_adjust(Cat, new_cat_event.event_text, cat, other_cat, other_clan_name,
                                       new_cat=created_cats[0])

        types = ["misc"]
        if "other_clan" in new_cat_event.tags:
            types.append("other_clans")
        game.cur_events_list.append(Single_Event(event_text, types, involved_cats))

        return created_cats

    @staticmethod
    def has_outside_cat():
        outside_cats = [i for i in Cat.all_cats.values() if i.status in ["kittypet", "loner", "rogue", "former Clancat"] and not i.dead and i.outside]
        return any(outside_cats)

    @staticmethod
    def select_outside_cat():
        outside_cats = [i for i in Cat.all_cats.values() if i.status in ["kittypet", "loner", "rogue", "former Clancat"] and not i.dead and i.outside]
        if outside_cats:
            return random.choice(outside_cats)
        else:
            return None
        
    @staticmethod
    def has_exiled_cat():
        exiled_cats = [i for i in Cat.all_cats.values() if i.status == "exiled" and not i.dead]
        return any(exiled_cats)

    @staticmethod
    def select_exiled_cat():
        exiled_cats = [i for i in Cat.all_cats.values() if i.status == "exiled" and not i.dead]
        if exiled_cats:
            return random.choice(exiled_cats)
        else:
            return None
        

    @staticmethod
    def update_cat_properties(cat):
        if cat.moons < 6:
            cat.status = 'kitten'
        elif cat.backstory in BACKSTORIES["backstory_categories"]['healer_backstories']:
            cat.status = 'medicine cat'
        else:
            cat.status = "warrior"
        cat.outside = False
        return cat
