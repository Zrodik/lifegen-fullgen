import os
import shutil
import threading
import time
from re import search as re_search
import platform
import ujson
import pygame
import pygame_gui
from sys import exit
from re import sub
from platform import system
from random import choice
import logging
import subprocess
import random


from scripts.cat.history import History
from scripts.cat.names import Name
from pygame_gui.elements import UIWindow

from scripts.housekeeping.datadir import get_save_dir, get_cache_dir, get_saved_images_dir, get_data_dir
from scripts.game_structure import image_cache
from scripts.game_structure.game_essentials import game, screen_x, screen_y
from scripts.game_structure.image_button import UIImageButton, UITextBoxTweaked
from scripts.housekeeping.progress_bar_updater import UIUpdateProgressBar
from scripts.housekeeping.update import self_update, UpdateChannel, get_latest_version_number
from scripts.event_class import Single_Event
from scripts.utility import scale, quit, update_sprite, scale_dimentions, logger, process_text
from scripts.game_structure.game_essentials import game, MANAGER
from scripts.housekeeping.version import get_version_info


class SaveCheck(UIWindow):
    def __init__(self, last_screen, isMainMenu, mm_btn):
        game.switches['window_open'] = True
        if game.is_close_menu_open:
            return
        game.is_close_menu_open = True
        super().__init__(scale(pygame.Rect((500, 400), (600, 400))),
                         window_display_title='Save Check',
                         object_id='#save_check_window',
                         resizable=False)

        self.clan_name = "UndefinedClan"
        if game.clan:
            self.clan_name = f"{game.clan.name}Clan"
        self.last_screen = last_screen
        self.isMainMenu = isMainMenu
        self.mm_btn = mm_btn
        # adding a variable for starting_height to make sure that this menu is always on top
        top_stack_menu_layer_height = 10000
        if (self.isMainMenu):
            self.mm_btn.disable()
            self.main_menu_button = UIImageButton(
                scale(pygame.Rect((146, 310), (305, 60))),
                "",
                object_id="#main_menu_button",
                starting_height=top_stack_menu_layer_height,
                container=self
            )
            self.message = f"Would you like to save your game before exiting to the Main Menu? If you don't, progress may be lost!"
        else:
            self.main_menu_button = UIImageButton(
                scale(pygame.Rect((146, 310), (305, 60))),
                "",
                object_id="#smallquit_button",
                starting_height=top_stack_menu_layer_height,
                container=self
            )
            self.message = f"Would you like to save your game before exiting? If you don't, progress may be lost!"

        self.game_over_message = UITextBoxTweaked(
            self.message,
            scale(pygame.Rect((40, 40), (520, -1))),
            line_spacing=1,
            object_id="#text_box_30_horizcenter",
            container=self
        )

        self.save_button = UIImageButton(scale(pygame.Rect((186, 230), (228, 60))),
                                         "",
                                         object_id="#save_button",
                                         starting_height=top_stack_menu_layer_height,
                                         container=self
                                         )
        self.save_button_saved_state = pygame_gui.elements.UIImage(
            scale(pygame.Rect((186, 230), (228, 60))),
            pygame.transform.scale(
                image_cache.load_image('resources/images/save_clan_saved.png'),
                (228, 60)),
            container=self)
        self.save_button_saved_state.hide()
        self.save_button_saving_state = pygame_gui.elements.UIImage(
            scale(pygame.Rect((186, 230), (228, 60))),
            pygame.transform.scale(
                image_cache.load_image(
                    'resources/images/save_clan_saving.png'),
                (228, 60)),
            container=self)
        self.save_button_saving_state.hide()

        self.back_button = UIImageButton(
            scale(pygame.Rect((540, 10), (44, 44))),
            "",
            object_id="#exit_window_button",
            starting_height=top_stack_menu_layer_height,
            container=self
        )

        self.back_button.enable()
        self.main_menu_button.enable()
        self.set_blocking(True)

    def process_event(self, event):
        super().process_event(event)

        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            if event.ui_element == self.main_menu_button:
                if self.isMainMenu:
                    game.is_close_menu_open = False
                    self.mm_btn.enable()
                    game.last_screen_forupdate = game.switches['cur_screen']
                    game.switches['cur_screen'] = 'start screen'
                    game.switch_screens = True
                    self.kill()
                    game.switches['window_open'] = False
                else:
                    game.is_close_menu_open = False
                    quit(savesettings=False, clearevents=False)
            elif event.ui_element == self.save_button:
                if game.clan is not None:
                    self.save_button_saving_state.show()
                    self.save_button.disable()
                    game.save_cats()
                    game.clan.save_clan()
                    game.clan.save_pregnancy(game.clan)
                    game.save_events()
                    self.save_button_saving_state.hide()
                    self.save_button_saved_state.show()
            elif event.ui_element == self.back_button:
                game.is_close_menu_open = False
                game.switches['window_open'] = False
                self.kill()
                if self.isMainMenu:
                    self.mm_btn.enable()

                # only allow one instance of this window


class DeleteCheck(UIWindow):
    def __init__(self, reloadscreen, clan_name):
        super().__init__(scale(pygame.Rect((500, 400), (600, 360))),
                         window_display_title='Delete Check',
                         object_id='#delete_check_window',
                         resizable=False)
        self.set_blocking(True)
        game.switches['window_open'] = True
        self.clan_name = clan_name
        self.reloadscreen = reloadscreen

        self.delete_check_message = UITextBoxTweaked(
            f"Do you wish to delete {str(self.clan_name + 'Clan')}? This is permanent and cannot be undone.",
            scale(pygame.Rect((40, 40), (520, -1))),
            line_spacing=1,
            object_id="#text_box_30_horizcenter",
            container=self
        )

        self.delete_it_button = UIImageButton(
            scale(pygame.Rect((142, 200), (306, 60))),
            "delete",
            object_id="#delete_it_button",
            container=self
        )
        self.go_back_button = UIImageButton(
            scale(pygame.Rect((142, 270), (306, 60))),
            "go back",
            object_id="#go_back_button",
            container=self
        )

        self.back_button = UIImageButton(
            scale(pygame.Rect((540, 10), (44, 44))),
            "",
            object_id="#exit_window_button",
            container=self
        )

        self.back_button.enable()

        self.go_back_button.enable()
        self.delete_it_button.enable()

    def process_event(self, event):
        super().process_event(event)

        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            if event.ui_element == self.delete_it_button:
                game.switches['window_open'] = False
                print("delete")
                rempath = get_save_dir() + "/" + self.clan_name
                shutil.rmtree(rempath)
                if os.path.exists(rempath + 'clan.json'):
                    os.remove(rempath + "clan.json")
                elif os.path.exists(rempath + 'clan.txt'):
                    os.remove(rempath + "clan.txt")
                else:
                    print("No clan.json/txt???? Clan prolly wasnt initalized kekw")
                self.kill()
                self.reloadscreen('switch clan screen')

            elif event.ui_element == self.go_back_button:
                game.switches['window_open'] = False
                self.kill()
            elif event.ui_element == self.back_button:
                game.switches['window_open'] = False
                game.is_close_menu_open = False
                self.kill()


class GameOver(UIWindow):
    def __init__(self, last_screen):
        super().__init__(scale(pygame.Rect((500, 400), (600, 360))),
                         window_display_title='Game Over',
                         object_id='#game_over_window',
                         resizable=False)
        self.set_blocking(True)
        game.switches['window_open'] = True
        self.clan_name = str(game.clan.name + 'Clan')
        self.last_screen = last_screen
        self.game_over_message = UITextBoxTweaked(
            f"{self.clan_name} has died out. For now, this is where their story ends. Perhaps it's time to tell a new "
            f"tale?",
            scale(pygame.Rect((40, 40), (520, -1))),
            line_spacing=1,
            object_id="",
            container=self
        )

        self.game_over_message = UITextBoxTweaked(
            f"(leaving will not erase the save file)",
            scale(pygame.Rect((40, 310), (520, -1))),
            line_spacing=.8,
            object_id="#text_box_22_horizcenter",
            container=self
        )

        self.begin_anew_button = UIImageButton(
            scale(pygame.Rect((50, 230), (222, 60))),
            "",
            object_id="#begin_anew_button",
            container=self
        )
        self.not_yet_button = UIImageButton(
            scale(pygame.Rect((318, 230), (222, 60))),
            "",
            object_id="#not_yet_button",
            container=self
        )

        self.not_yet_button.enable()
        self.begin_anew_button.enable()

    def process_event(self, event):
        super().process_event(event)

        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            if event.ui_element == self.begin_anew_button:
                game.last_screen_forupdate = game.switches['cur_screen']
                game.switches['cur_screen'] = 'start screen'
                game.switch_screens = True
                game.switches['window_open'] = False
                self.kill()
            elif event.ui_element == self.not_yet_button:
                game.switches['window_open'] = False
                self.kill()


class ChangeCatName(UIWindow):
    """This window allows the user to change the cat's name"""

    def __init__(self, cat):
        super().__init__(scale(pygame.Rect((600, 430), (800, 370))),
                         window_display_title='Change Cat Name',
                         object_id='#change_cat_name_window',
                         resizable=False)
        game.switches['window_open'] = True
        self.the_cat = cat
        self.back_button = UIImageButton(
            scale(pygame.Rect((740, 10), (44, 44))),
            "",
            object_id="#exit_window_button",
            container=self
        )

        self.specsuffic_hidden = self.the_cat.name.specsuffix_hidden

        self.heading = pygame_gui.elements.UITextBox(f"-Change {self.the_cat.name}'s Name-",
                                                     scale(pygame.Rect(
                                                         (0, 20), (800, 80))),
                                                     object_id="#text_box_30_horizcenter",
                                                     manager=MANAGER,
                                                     container=self)

        self.name_changed = pygame_gui.elements.UITextBox("Name Changed!", scale(pygame.Rect((490, 260), (800, 80))),
                                                          visible=False,
                                                          object_id="#text_box_30_horizleft",
                                                          manager=MANAGER,
                                                          container=self)

        self.done_button = UIImageButton(scale(pygame.Rect((323, 270), (154, 60))), "",
                                         object_id="#done_button",
                                         manager=MANAGER,
                                         container=self)

        x_pos, y_pos = 75, 35

        self.prefix_entry_box = pygame_gui.elements.UITextEntryLine(
            scale(pygame.Rect((0 + x_pos, 100 + y_pos), (240, 60))),
            initial_text=self.the_cat.name.prefix,
            manager=MANAGER,
            container=self)

        self.random_prefix = UIImageButton(scale(pygame.Rect((245 + x_pos, 97 + y_pos), (68, 68))), "",
                                           object_id="#random_dice_button",
                                           manager=MANAGER,
                                           container=self,
                                           tool_tip_text='Randomize the prefix')

        self.random_suffix = UIImageButton(scale(pygame.Rect((563 + x_pos, 97 + y_pos), (68, 68))), "",
                                           object_id="#random_dice_button",
                                           manager=MANAGER,
                                           container=self,
                                           tool_tip_text='Randomize the suffix')

        # 636
        self.toggle_spec_block_on = UIImageButton(scale(pygame.Rect((405 + x_pos, 160 + y_pos), (68, 68))), "",
                                                  object_id="#unchecked_checkbox",
                                                  tool_tip_text=f"Remove the cat's special suffix",
                                                  manager=MANAGER,
                                                  container=self)

        self.toggle_spec_block_off = UIImageButton(scale(pygame.Rect((405 + x_pos, 160 + y_pos), (68, 68))), "",
                                                   object_id="#checked_checkbox",
                                                   tool_tip_text="Re-enable the cat's special suffix", manager=MANAGER,
                                                   container=self)

        if self.the_cat.name.status in self.the_cat.name.names_dict["special_suffixes"]:
            self.suffix_entry_box = pygame_gui.elements.UITextEntryLine(
                scale(pygame.Rect((318 + x_pos, 100 + y_pos), (240, 60))),
                placeholder_text=self.the_cat.name.names_dict["special_suffixes"]
                [self.the_cat.name.status], manager=MANAGER,
                container=self)
            if not self.the_cat.name.specsuffix_hidden:
                self.toggle_spec_block_on.show()
                self.toggle_spec_block_on.enable()
                self.toggle_spec_block_off.hide()
                self.toggle_spec_block_off.disable()
                self.random_suffix.disable()
                self.suffix_entry_box.disable()
            else:
                self.toggle_spec_block_on.hide()
                self.toggle_spec_block_on.disable()
                self.toggle_spec_block_off.show()
                self.toggle_spec_block_off.enable()
                self.random_suffix.enable()
                self.suffix_entry_box.enable()
                self.suffix_entry_box.set_text(self.the_cat.name.suffix)

        else:
            self.toggle_spec_block_on.disable()
            self.toggle_spec_block_on.hide()
            self.toggle_spec_block_off.disable()
            self.toggle_spec_block_off.hide()
            self.suffix_entry_box = pygame_gui.elements.UITextEntryLine(
                scale(pygame.Rect((318 + x_pos, 100 + y_pos), (240, 60))),
                initial_text=self.the_cat.name.suffix, manager=MANAGER,
                container=self)
        self.set_blocking(True)

    def process_event(self, event):
        super().process_event(event)

        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            if event.ui_element == self.done_button:
                old_name = str(self.the_cat.name)

                self.the_cat.specsuffix_hidden = self.specsuffic_hidden
                self.the_cat.name.specsuffix_hidden = self.specsuffic_hidden

                # Note: Prefixes are not allowed be all spaces or empty, but they can have spaces in them.
                if sub(r'[^A-Za-z0-9 ]+', '', self.prefix_entry_box.get_text()) != '':
                    self.the_cat.name.prefix = sub(
                        r'[^A-Za-z0-9 ]+', '', self.prefix_entry_box.get_text())

                # Suffixes can be empty, if you want. However, don't change the suffix if it's currently being hidden
                # by a special suffix.
                if self.the_cat.name.status not in self.the_cat.name.names_dict["special_suffixes"] or \
                        self.the_cat.name.specsuffix_hidden:
                    self.the_cat.name.suffix = sub(
                        r'[^A-Za-z0-9 ]+', '', self.suffix_entry_box.get_text())
                    self.name_changed.show()

                if old_name != str(self.the_cat.name):
                    self.name_changed.show()
                    self.heading.set_text(
                        f"-Change {self.the_cat.name}'s Name-")
                else:
                    self.name_changed.hide()

            elif event.ui_element == self.random_prefix:
                if self.suffix_entry_box.text:
                    use_suffix = self.suffix_entry_box.text
                else:
                    use_suffix = self.the_cat.name.suffix
                self.prefix_entry_box.set_text(Name(self.the_cat.status,
                                                    None,
                                                    use_suffix,
                                                    self.the_cat.pelt.colour,
                                                    self.the_cat.pelt.eye_colour,
                                                    self.the_cat.pelt.name,
                                                    self.the_cat.pelt.tortiepattern).prefix)
            elif event.ui_element == self.random_suffix:
                if self.prefix_entry_box.text:
                    use_prefix = self.prefix_entry_box.text
                else:
                    use_prefix = self.the_cat.name.prefix
                self.suffix_entry_box.set_text(Name(self.the_cat.status,
                                                    use_prefix,
                                                    None,
                                                    self.the_cat.pelt.colour,
                                                    self.the_cat.pelt.eye_colour,
                                                    self.the_cat.pelt.name,
                                                    self.the_cat.pelt.tortiepattern).suffix)
            elif event.ui_element == self.toggle_spec_block_on:
                self.specsuffic_hidden = True
                self.suffix_entry_box.enable()
                self.random_suffix.enable()
                self.toggle_spec_block_on.disable()
                self.toggle_spec_block_on.hide()
                self.toggle_spec_block_off.enable()
                self.toggle_spec_block_off.show()
                self.suffix_entry_box.set_text(self.the_cat.name.suffix)
            elif event.ui_element == self.toggle_spec_block_off:
                self.specsuffic_hidden = False
                self.random_suffix.disable()
                self.toggle_spec_block_off.disable()
                self.toggle_spec_block_off.hide()
                self.toggle_spec_block_on.enable()
                self.toggle_spec_block_on.show()
                self.suffix_entry_box.set_text("")
                self.suffix_entry_box.rebuild()
                self.suffix_entry_box.disable()
            elif event.ui_element == self.back_button:
                game.switches['window_open'] = False
                game.all_screens['profile screen'].exit_screen()
                game.all_screens['profile screen'].screen_switches()
                self.kill()


class SpecifyCatGender(UIWindow):
    """This window allows the user to specify the cat's gender"""

    def __init__(self, cat):
        super().__init__(scale(pygame.Rect((600, 430), (800, 370))),
                         window_display_title='Change Cat Gender',
                         object_id='#change_cat_gender_window',
                         resizable=False)
        game.switches['window_open'] = True
        self.the_cat = cat
        self.back_button = UIImageButton(
            scale(pygame.Rect((740, 10), (44, 44))),
            "",
            object_id="#exit_window_button",
            container=self
        )
        self.heading = pygame_gui.elements.UITextBox(f"-Change {self.the_cat.name}'s Gender-"
                                                     f"<br> You can set this to anything! "
                                                     f"Gender alignment does not affect gameplay.",
                                                     scale(pygame.Rect(
                                                         (20, 20), (760, 150))),
                                                     object_id="#text_box_30_horizcenter_spacing_95",
                                                     manager=MANAGER,
                                                     container=self)

        self.gender_changed = pygame_gui.elements.UITextBox("Gender Changed!",
                                                            scale(pygame.Rect(
                                                                (490, 260), (800, 80))),
                                                            visible=False,
                                                            object_id="#text_box_30_horizleft",
                                                            manager=MANAGER,
                                                            container=self)

        self.done_button = UIImageButton(scale(pygame.Rect((323, 270), (154, 60))), "",
                                         object_id="#done_button",
                                         manager=MANAGER,
                                         container=self)

        self.gender_entry_box = pygame_gui.elements.UITextEntryLine(scale(pygame.Rect((200, 180), (400, 60))),
                                                                    placeholder_text=self.the_cat.genderalign,
                                                                    manager=MANAGER,
                                                                    container=self)
        self.set_blocking(True)

    def process_event(self, event):
        super().process_event(event)

        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            if event.ui_element == self.done_button:
                if sub(r'[^A-Za-z0-9 ]+', "", self.gender_entry_box.get_text()) != "":
                    self.the_cat.genderalign = sub(
                        r'[^A-Za-z0-9 ]+', "", self.gender_entry_box.get_text())
                    self.gender_changed.show()
            elif event.ui_element == self.back_button:
                game.switches['window_open'] = False
                game.all_screens['profile screen'].exit_screen()
                game.all_screens['profile screen'].screen_switches()
                self.kill()


class KillCat(UIWindow):
    """This window allows the user to specify the cat's gender"""

    def __init__(self, cat):
        super().__init__(scale(pygame.Rect((600, 400), (900, 400))),
                         window_display_title='Kill Cat',
                         object_id='#change_cat_gender_window',
                         resizable=False)
        self.history = History()
        game.switches['window_open'] = True
        self.the_cat = cat
        self.take_all = False
        cat_dict = {
            "m_c": (str(self.the_cat.name), choice(self.the_cat.pronouns))
        }
        self.back_button = UIImageButton(
            scale(pygame.Rect((840, 10), (44, 44))),
            "",
            object_id="#exit_window_button",
            container=self
        )
        cat_dict = {
            "m_c": (str(self.the_cat.name), choice(self.the_cat.pronouns))
        }
        self.heading = pygame_gui.elements.UITextBox(f"<b>-- How did this cat die? --</b>",
                                                     scale(pygame.Rect(
                                                         (20, 20), (860, 150))),
                                                     object_id="#text_box_30_horizcenter_spacing_95",
                                                     manager=MANAGER,
                                                     container=self)

        self.one_life_check = UIImageButton(scale(pygame.Rect(
            (50, 300), (68, 68))),
            "",
            object_id="#unchecked_checkbox",
            tool_tip_text=process_text(
                'If this is checked, the leader will lose all {PRONOUN/m_c/poss} lives', cat_dict),
            manager=MANAGER,
            container=self
        )
        self.all_lives_check = UIImageButton(scale(pygame.Rect(
            (50, 300), (68, 68))),
            "",
            object_id="#checked_checkbox",
            tool_tip_text=process_text(
                'If this is checked, the leader will lose all {PRONOUN/m_c/poss} lives', cat_dict),
            manager=MANAGER,
            container=self
        )

        if self.the_cat.status == 'leader':
            self.done_button = UIImageButton(scale(pygame.Rect((695, 305), (154, 60))), "",
                                             object_id="#done_button",
                                             manager=MANAGER,
                                             container=self)

            self.prompt = process_text(
                'This cat died when {PRONOUN/m_c/subject}...', cat_dict)
            self.initial = process_text(
                '{VERB/m_c/were/was} killed by a higher power.', cat_dict)

            self.all_lives_check.hide()
            self.life_text = pygame_gui.elements.UITextBox('Take all the leader\'s lives',
                                                           scale(pygame.Rect(
                                                               (120, 295), (900, 80))),
                                                           object_id="#text_box_30_horizleft",
                                                           manager=MANAGER,
                                                           container=self)
            self.beginning_prompt = pygame_gui.elements.UITextBox(self.prompt,
                                                                  scale(pygame.Rect(
                                                                      (50, 60), (900, 80))),
                                                                  object_id="#text_box_30_horizleft",
                                                                  manager=MANAGER,
                                                                  container=self)

            self.death_entry_box = pygame_gui.elements.UITextEntryBox(scale(pygame.Rect((50, 130), (800, 150))),
                                                                      initial_text=self.initial,
                                                                      object_id="text_entry_line",
                                                                      manager=MANAGER,
                                                                      container=self)

        elif History.get_death_or_scars(self.the_cat, death=True):
            # This should only occur for retired leaders.

            self.prompt = process_text(
                'This cat died when {PRONOUN/m_c/subject}...', cat_dict)
            self.initial = process_text(
                '{VERB/m_c/were/was} killed by something unknowable to even StarClan', cat_dict)
            self.all_lives_check.hide()
            self.one_life_check.hide()

            self.beginning_prompt = pygame_gui.elements.UITextBox(self.prompt,
                                                                  scale(pygame.Rect(
                                                                      (50, 60), (900, 80))),
                                                                  object_id="#text_box_30_horizleft",
                                                                  manager=MANAGER,
                                                                  container=self)

            self.death_entry_box = pygame_gui.elements.UITextEntryBox(scale(pygame.Rect((50, 130), (800, 150))),
                                                                      initial_text=self.initial,
                                                                      object_id="text_entry_line",
                                                                      manager=MANAGER,
                                                                      container=self)

            self.done_button = UIImageButton(scale(pygame.Rect((373, 305), (154, 60))), "",
                                             object_id="#done_button",
                                             manager=MANAGER,
                                             container=self)
        else:
            self.initial = 'This cat was killed by a higher power.'
            self.prompt = None
            self.all_lives_check.hide()
            self.one_life_check.hide()

            self.death_entry_box = pygame_gui.elements.UITextEntryBox(scale(pygame.Rect((50, 110), (800, 150))),
                                                                      initial_text=self.initial,
                                                                      object_id="text_entry_line",
                                                                      manager=MANAGER,
                                                                      container=self)

            self.done_button = UIImageButton(scale(pygame.Rect((373, 305), (154, 60))), "",
                                             object_id="#done_button",
                                             manager=MANAGER,
                                             container=self)
        self.set_blocking(True)

    def process_event(self, event):
        super().process_event(event)

        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            if event.ui_element == self.done_button:
                death_message = sub(
                    r"[^A-Za-z0-9<->/.()*'&#!?,| _]+", "", self.death_entry_box.get_text())
                if self.the_cat.status == 'leader':

                    if death_message.startswith('was'):
                        death_message = death_message.replace(
                            "was", '{VERB/m_c/were/was}', 1)
                    elif death_message.startswith('were'):
                        death_message = death_message.replace(
                            "were", '{VERB/m_c/were/was}', 1)

                    if self.take_all:
                        game.clan.leader_lives = 0
                    else:
                        game.clan.leader_lives -= 1

                self.the_cat.die()
                self.history.add_death(self.the_cat, death_message)
                update_sprite(self.the_cat)
                game.switches['window_open'] = False
                game.all_screens['profile screen'].exit_screen()
                game.all_screens['profile screen'].screen_switches()
                self.kill()
            elif event.ui_element == self.all_lives_check:
                self.take_all = False
                self.all_lives_check.hide()
                self.one_life_check.show()
            elif event.ui_element == self.one_life_check:
                self.take_all = True
                self.all_lives_check.show()
                self.one_life_check.hide()
            elif event.ui_element == self.back_button:
                game.switches['window_open'] = False
                game.all_screens['profile screen'].exit_screen()
                game.all_screens['profile screen'].screen_switches()
                self.kill()


class UpdateWindow(UIWindow):
    def __init__(self, last_screen, announce_restart_callback):
        super().__init__(scale(pygame.Rect((500, 400), (600, 320))),
                         window_display_title='Game Over',
                         object_id='#game_over_window',
                         resizable=False)
        self.last_screen = last_screen
        self.update_message = UITextBoxTweaked(
            f"Update in progress.",
            scale(pygame.Rect((40, 20), (520, -1))),
            line_spacing=1,
            object_id="#text_box_30_horizcenter",
            container=self
        )
        self.announce_restart_callback = announce_restart_callback

        self.step_text = UITextBoxTweaked(
            f"Downloading update...",
            scale(pygame.Rect((40, 80), (520, -1))),
            line_spacing=1,
            object_id="#text_box_30_horizcenter",
            container=self
        )

        self.progress_bar = UIUpdateProgressBar(
            scale(pygame.Rect((40, 130), (520, 70))),
            self.step_text,
            object_id="progress_bar",
            container=self,
        )

        self.update_thread = threading.Thread(target=self_update, daemon=True, args=(
            UpdateChannel(get_version_info().release_channel), self.progress_bar, announce_restart_callback))
        self.update_thread.start()

        self.cancel_button = UIImageButton(
            scale(pygame.Rect((400, 230), (156, 60))),
            "",
            object_id="#cancel_button",
            container=self
        )

        self.cancel_button.enable()

    def process_event(self, event):
        super().process_event(event)

        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            if event.ui_element == self.cancel_button:
                self.kill()


class AnnounceRestart(UIWindow):
    def __init__(self, last_screen):
        super().__init__(scale(pygame.Rect((500, 400), (600, 180))),
                         window_display_title='Game Over',
                         object_id='#game_over_window',
                         resizable=False)
        self.last_screen = last_screen
        self.announce_message = UITextBoxTweaked(
            f"The game will automatically restart in 3...",
            scale(pygame.Rect((40, 40), (520, -1))),
            line_spacing=1,
            object_id="#text_box_30_horizcenter",
            container=self
        )

        threading.Thread(target=self.update_text, daemon=True).start()

    def update_text(self):
        for i in range(2, 0, -1):
            time.sleep(1)
            self.announce_message.set_text(
                f"The game will automatically restart in {i}...")


class UpdateAvailablePopup(UIWindow):
    def __init__(self, last_screen, show_checkbox: bool = False):
        super().__init__(scale(pygame.Rect((400, 400), (800, 460))),
                         window_display_title='Update available',
                         object_id='#game_over_window',
                         resizable=False)
        self.set_blocking(True)
        game.switches['window_open'] = True
        self.last_screen = last_screen

        self.begin_update_title = UIImageButton(
            scale(pygame.Rect((195, 30), (400, 81))),
            "",
            object_id="#new_update_button",
            container=self
        )

        latest_version_number = "{:.16}".format(get_latest_version_number())
        current_version_number = "{:.16}".format(
            get_version_info().version_number)

        self.game_over_message = UITextBoxTweaked(
            f"<strong>Update to LifeGen {latest_version_number}</strong>",
            scale(pygame.Rect((20, 160), (800, -1))),
            line_spacing=.8,
            object_id="#update_popup_title",
            container=self
        )

        self.game_over_message = UITextBoxTweaked(
            f"Your current version: {current_version_number}",
            scale(pygame.Rect((22, 200), (800, -1))),
            line_spacing=.8,
            object_id="#text_box_current_version",
            container=self
        )

        self.game_over_message = UITextBoxTweaked(
            f"Install update now?",
            scale(pygame.Rect((20, 262), (400, -1))),
            line_spacing=.8,
            object_id="#text_box_30",
            container=self
        )

        self.box_unchecked = UIImageButton(scale(pygame.Rect((15, 366), (68, 68))), "", object_id="#unchecked_checkbox",
                                           container=self)
        self.box_checked = UIImageButton(scale(pygame.Rect((15, 366), (68, 68))), "", object_id="#checked_checkbox",
                                         container=self)
        self.box_text = UITextBoxTweaked(
            f"Don't ask again",
            scale(pygame.Rect((78, 370), (250, -1))),
            line_spacing=.8,
            object_id="#text_box_30",
            container=self
        )

        self.continue_button = UIImageButton(
            scale(pygame.Rect((556, 370), (204, 60))),
            "",
            object_id="#continue_button_small",
            container=self
        )

        self.cancel_button = UIImageButton(
            scale(pygame.Rect((374, 370), (156, 60))),
            "",
            object_id="#cancel_button",
            container=self
        )

        self.close_button = UIImageButton(
            scale(pygame.Rect((740, 10), (44, 44))),
            "",
            object_id="#exit_window_button",
            container=self
        )

        if show_checkbox:
            self.box_unchecked.enable()
            self.box_checked.hide()
        else:
            self.box_checked.hide()
            self.box_unchecked.hide()
            self.box_text.hide()

        self.continue_button.enable()
        self.cancel_button.enable()
        self.close_button.enable()

    def process_event(self, event):
        super().process_event(event)

        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            if event.ui_element == self.continue_button:
                game.switches['window_open'] = False
                self.x = UpdateWindow(
                    game.switches['cur_screen'], self.announce_restart_callback)
                self.kill()
            elif event.ui_element == self.close_button or event.ui_element == self.cancel_button:
                game.switches['window_open'] = False
                self.kill()
            elif event.ui_element == self.box_unchecked:
                self.box_unchecked.disable()
                self.box_unchecked.hide()
                self.box_checked.enable()
                self.box_checked.show()
                with open(f"{get_cache_dir()}/suppress_update_popup", 'w') as write_file:
                    write_file.write(get_latest_version_number())
            elif event.ui_element == self.box_checked:
                self.box_checked.disable()
                self.box_checked.hide()
                self.box_unchecked.enable()
                self.box_unchecked.show()
                if os.path.exists(f"{get_cache_dir()}/suppress_update_popup"):
                    os.remove(f"{get_cache_dir()}/suppress_update_popup")

    def announce_restart_callback(self):
        self.x.kill()
        y = AnnounceRestart(game.switches['cur_screen'])
        y.update(1)


class ChangelogPopup(UIWindow):
    def __init__(self, last_screen):
        super().__init__(scale(pygame.Rect((300, 300), (1000, 800))),
                         window_display_title='Changelog',
                         object_id='#game_over_window',
                         resizable=False)
        self.set_blocking(True)
        game.switches['window_open'] = True
        self.last_screen = last_screen
        self.changelog_popup_title = UITextBoxTweaked(
            f"<strong>What's New</strong>",
            scale(pygame.Rect((40, 20), (960, -1))),
            line_spacing=1,
            object_id="#changelog_popup_title",
            container=self
        )

        current_version_number = "{:.16}".format(
            get_version_info().version_number)

        self.changelog_popup_subtitle = UITextBoxTweaked(
            f"Version {current_version_number}",
            scale(pygame.Rect((40, 70), (960, -1))),
            line_spacing=1,
            object_id="#changelog_popup_subtitle",
            container=self
        )

        self.scrolling_container = pygame_gui.elements.UIScrollingContainer(
            scale(pygame.Rect((20, 130), (960, 650))),
            container=self,
            manager=MANAGER)

        dynamic_changelog = False
        
        with open("changelog.txt", "r") as read_file:
            file_cont = read_file.read()

        self.changelog_text = UITextBoxTweaked(
            file_cont,
            scale(pygame.Rect((20, 130), (960, 650))),
            object_id="#text_box_30",
            line_spacing=.95,
            starting_height=2,
            container=self,
            manager=MANAGER)

        self.close_button = UIImageButton(
            scale(pygame.Rect((940, 10), (44, 44))),
            "",
            object_id="#exit_window_button",
            starting_height=2,
            container=self
        )


    def process_event(self, event):
        super().process_event(event)

        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            if event.ui_element == self.close_button:
                game.switches['window_open'] = False
                self.kill()


class RelationshipLog(UIWindow):
    """This window allows the user to see the relationship log of a certain relationship."""

    def __init__(self, relationship, disable_button_list, hide_button_list):
        super().__init__(scale(pygame.Rect((546, 245), (1010, 1100))),
                         window_display_title='Relationship Log',
                         object_id='#relationship_log_window',
                         resizable=False)
        game.switches['window_open'] = True
        self.hide_button_list = hide_button_list
        for button in self.hide_button_list:
            button.hide()

        self.exit_button = UIImageButton(
            scale(pygame.Rect((940, 15), (44, 44))),
            "",
            object_id="#exit_window_button",
            container=self
        )
        self.back_button = UIImageButton(
            scale(pygame.Rect((50, 1290), (210, 60))), "", object_id="#back_button")
        self.log_icon = UIImageButton(
            scale(pygame.Rect((445, 808), (68, 68))), "", object_id="#log_icon")
        self.closing_buttons = [self.exit_button,
                                self.back_button, self.log_icon]

        self.disable_button_list = disable_button_list
        for button in self.disable_button_list:
            button.disable()

        """if game.settings["fullscreen"]:
            img_path = "resources/images/spacer.png"
        else:
            img_path = "resources/images/spacer_small.png"""

        opposite_log_string = None
        if not relationship.opposite_relationship:
            relationship.link_relationship()
        if relationship.opposite_relationship and len(relationship.opposite_relationship.log) > 0:
            opposite_log_string = f"{f'<br>-----------------------------<br>'.join(relationship.opposite_relationship.log)}<br>"

        log_string = f"{f'<br>-----------------------------<br>'.join(relationship.log)}<br>" if len(relationship.log) > 0 else\
            "There are no relationship logs."

        if not opposite_log_string:
            self.log = pygame_gui.elements.UITextBox(log_string,
                                                     scale(pygame.Rect(
                                                         (30, 70), (953, 850))),
                                                     object_id="#text_box_30_horizleft",
                                                     manager=MANAGER,
                                                     container=self)
        else:
            self.log = pygame_gui.elements.UITextBox(log_string,
                                                     scale(pygame.Rect(
                                                         (30, 70), (953, 500))),
                                                     object_id="#text_box_30_horizleft",
                                                     manager=MANAGER,
                                                     container=self)
            self.opp_heading = pygame_gui.elements.UITextBox("<u><b>OTHER PERSPECTIVE</b></u>",
                                                             scale(pygame.Rect(
                                                                 (30, 550), (953, 560))),
                                                             object_id="#text_box_30_horizleft",
                                                             manager=MANAGER,
                                                             container=self)
            self.opp_heading.disable()
            self.opp_log = pygame_gui.elements.UITextBox(opposite_log_string,
                                                         scale(pygame.Rect(
                                                             (30, 610), (953, 465))),
                                                         object_id="#text_box_30_horizleft",
                                                         manager=MANAGER,
                                                         container=self)

        self.set_blocking(True)

    def closing_process(self):
        """Handles to enable and kill all processes when a exit button is clicked."""
        game.switches['window_open'] = False
        for button in self.disable_button_list:
            button.enable()
        for button in self.hide_button_list:
            button.show()
            button.enable()
        self.log_icon.kill()
        self.exit_button.kill()
        self.back_button.kill()
        self.kill()

    def process_event(self, event):
        super().process_event(event)

        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            if event.ui_element in self.closing_buttons:
                self.closing_process()


class SaveError(UIWindow):
    def __init__(self, error_text):
        super().__init__(scale(pygame.Rect((300, 300), (1000, 800))),
                         window_display_title='Changelog',
                         object_id='#game_over_window',
                         resizable=False)
        self.set_blocking(True)
        game.switches['window_open'] = True
        self.changelog_popup_title = pygame_gui.elements.UITextBox(
            f"<strong>Saving Failed!</strong>\n\n{error_text}",
            scale(pygame.Rect((40, 20), (890, 750))),
            object_id="#text_box_30",
            container=self
        )

        self.close_button = UIImageButton(
            scale(pygame.Rect((940, 10), (44, 44))),
            "",
            object_id="#exit_window_button",
            starting_height=2,
            container=self
        )

    def process_event(self, event):
        super().process_event(event)

        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            if event.ui_element == self.close_button:
                game.switches['window_open'] = False
                self.kill()


class SaveAsImage(UIWindow):
    def __init__(self, image_to_save, file_name):
        super().__init__(scale(pygame.Rect((400, 350), (800, 500))),
                         object_id="#game_over_window",
                         resizable=False)

        self.set_blocking(True)
        game.switches['window_open'] = True

        self.image_to_save = image_to_save
        self.file_name = file_name
        self.scale_factor = 1

        button_layout_rect = scale(pygame.Rect((0, 10), (44, 44)))
        button_layout_rect.topright = scale_dimentions((-2, 10))

        self.close_button = UIImageButton(
            button_layout_rect,
            "",
            object_id="#exit_window_button",
            starting_height=2,
            container=self,
            anchors={'right': 'right',
                     'top': 'top'}
        )

        self.save_as_image = UIImageButton(
            scale(pygame.Rect((0, 180), (270, 60))),
            "",
            object_id="#save_image_button",
            starting_height=2,
            container=self,
            anchors={'centerx': 'centerx'}
        )

        self.open_data_directory_button = UIImageButton(
            scale(pygame.Rect((0, 350), (356, 60))),
            "",
            object_id="#open_data_directory_button",
            container=self,
            starting_height=2,
            tool_tip_text="Opens the data directory. "
                          "This is where save files, images, "
                          "and logs are stored.",
            anchors={'centerx': 'centerx'}
        )

        self.small_size_button = UIImageButton(
            scale(pygame.Rect((109, 100), (194, 60))),
            "",
            object_id="#image_small_button",
            container=self,
            starting_height=2
        )
        self.small_size_button.disable()

        self.medium_size_button = UIImageButton(
            scale(pygame.Rect((303, 100), (194, 60))),
            "",
            object_id="#image_medium_button",
            container=self,
            starting_height=2
        )

        self.large_size_button = UIImageButton(
            scale(pygame.Rect((497, 100), (194, 60))),
            "",
            object_id="#image_large_button",
            container=self,
            starting_height=2
        )

        self.confirm_text = pygame_gui.elements.UITextBox(
            "",
            scale(pygame.Rect((10, 250), (780, 90))),
            object_id="#text_box_26_horizcenter_vertcenter_spacing_95",
            container=self,
            starting_height=2
        )

    def save_image(self):
        file_name = self.file_name
        file_number = ""
        i = 0
        while True:
            if os.path.isfile(f"{get_saved_images_dir()}/{file_name + file_number}.png"):
                i += 1
                file_number = f"_{i}"
            else:
                break

        scaled_image = pygame.transform.scale_by(
            self.image_to_save, self.scale_factor)
        pygame.image.save(
            scaled_image, f"{get_saved_images_dir()}/{file_name + file_number}.png")
        return f"{file_name + file_number}.png"

    def process_event(self, event) -> bool:
        super().process_event(event)

        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            if event.ui_element == self.close_button:
                game.switches['window_open'] = False
                self.kill()
            elif event.ui_element == self.open_data_directory_button:
                if system() == 'Darwin':
                    subprocess.Popen(["open", "-R", get_data_dir()])
                elif system() == 'Windows':
                    os.startfile(get_data_dir())  # pylint: disable=no-member
                elif system() == 'Linux':
                    try:
                        subprocess.Popen(['xdg-open', get_data_dir()])
                    except OSError:
                        logger.exception("Failed to call to xdg-open.")
                return
            elif event.ui_element == self.save_as_image:
                file_name = self.save_image()
                self.confirm_text.set_text(
                    f"Saved as {file_name} in the saved_images folder")
            elif event.ui_element == self.small_size_button:
                self.scale_factor = 1
                self.small_size_button.disable()
                self.medium_size_button.enable()
                self.large_size_button.enable()
            elif event.ui_element == self.medium_size_button:
                self.scale_factor = 4
                self.small_size_button.enable()
                self.medium_size_button.disable()
                self.large_size_button.enable()
            elif event.ui_element == self.large_size_button:
                self.scale_factor = 6
                self.small_size_button.enable()
                self.medium_size_button.enable()
                self.large_size_button.disable()


class EventLoading(UIWindow):
    def __init__(self, pos):
        
        if pos is None: 
            pos = (800, 700)
        
        super().__init__(scale(pygame.Rect(pos, (200, 200))),
                         window_display_title='Game Over',
                         object_id='#loading_window',
                         resizable=False)

        self.set_blocking(True)
        game.switches['window_open'] = True

        self.frames = self.load_images()
        self.end_animation = False

        self.animated_image = pygame_gui.elements.UIImage(
            scale(pygame.Rect(0, 0, 200, 200)), self.frames[0], container=self)

        self.animation_thread = threading.Thread(target=self.animate)
        self.animation_thread.start()

    @staticmethod
    def load_images():
        frames = []
        for i in range(0, 16):
            frames.append(pygame.image.load(
                f"resources/images/loading_animate/timeskip/{i}.png"))

        return frames

    def animate(self):

        i = 0
        while True:
            if self.end_animation:
                break

            i += 1
            if i >= len(self.frames):
                i = 0

            self.animated_image.set_image(self.frames[i])

            time.sleep(0.125)

    def kill(self):
        self.end_animation = True
        game.switches['window_open'] = False
        super().kill()
    
class PickPath(UIWindow):
    def __init__(self, last_screen):
        super().__init__(scale(pygame.Rect((500, 400), (800, 500))),
                         window_display_title='Choose your Path',
                         object_id='#game_over_window',
                         resizable=False)
        self.set_blocking(True)
        game.switches['window_open'] = True
        self.clan_name = str(game.clan.name + 'Clan')
        self.last_screen = last_screen
        self.pick_path_message = UITextBoxTweaked(
            f"You have an important decision to make...",
            scale(pygame.Rect((40, 40), (720, -1))),
            line_spacing=1,
            object_id="#text_box_30_horizcenter",
            container=self
        )

        self.begin_anew_button = UIImageButton(
            scale(pygame.Rect((30, 190), (150, 150))),
            "",
            object_id="#med",
            container=self,
            tool_tip_text='Choose to become a medicine cat apprentice'
        )
        self.not_yet_button = UIImageButton(
            scale(pygame.Rect((220, 190), (150, 150))),
            "",
            object_id="#warrior",
            container=self,
            tool_tip_text='Choose to become a warrior apprentice'

        )
        self.mediator_button = UIImageButton(
            scale(pygame.Rect((410, 190), (150, 150))),
            "",
            object_id="#mediator",
            container=self,
            tool_tip_text='Choose to become a mediator apprentice'

        )
        self.queen_button = UIImageButton(
            scale(pygame.Rect((600, 190), (150, 150))),
            "",
            object_id="#queen",
            container=self,
            tool_tip_text="Choose to become a queen's apprentice"

        )
        self.random_button = UIImageButton(
            scale(pygame.Rect((345, 370), (100, 100))),
            "",
            object_id="#random_dice_button",
            container=self,
            tool_tip_text='Random'

        )

        self.not_yet_button.enable()
        self.begin_anew_button.enable()
        self.mediator_button.enable()
        self.random_button.enable()



    def process_event(self, event):
        super().process_event(event)

        try:

            if event.type == pygame_gui.UI_BUTTON_START_PRESS:
                if event.ui_element == self.begin_anew_button:
                    game.switches['window_open'] = False
                    if game.clan.your_cat.moons < 12:
                        game.clan.your_cat.status = 'medicine cat apprentice'
                    else:
                        game.clan.your_cat.status = 'medicine cat'
                    self.kill()
                elif event.ui_element == self.not_yet_button:
                    game.switches['window_open'] = False
                    if game.clan.your_cat.moons < 12:
                        game.clan.your_cat.status = 'apprentice'
                    else:
                        game.clan.your_cat.status = 'warrior'
                    self.kill()
                elif event.ui_element == self.mediator_button:
                    game.switches['window_open'] = False
                    if game.clan.your_cat.moons < 12:
                        game.clan.your_cat.status = 'mediator apprentice'
                    else:
                        game.clan.your_cat.status = 'mediator'
                    self.kill()
                elif event.ui_element == self.queen_button:
                    game.switches['window_open'] = False
                    if game.clan.your_cat.moons < 12:
                        game.clan.your_cat.status = "queen's apprentice"
                    else:
                        game.clan.your_cat.status = "queen"
                    self.kill()
                elif event.ui_element == self.random_button:
                    game.switches['window_open'] = False
                    if game.clan.your_cat.moons < 12:
                        game.clan.your_cat.status = random.choice(['mediator apprentice','apprentice','medicine cat apprentice', "queen's apprentice"])
                    else:
                        game.clan.your_cat.status = random.choice(['mediator','warrior','medicine cat', "queen"])
                    
                    self.kill()
        except:
            print('Error with PickPath window!')
                
class DeathScreen(UIWindow):
    def __init__(self, last_screen):
        super().__init__(scale(pygame.Rect((400, 400), (780, 500))),
                         window_display_title='You have died',
                         object_id='#game_over_window',
                         resizable=False)
        self.set_blocking(True)
        game.switches['window_open'] = True
        self.clan_name = str(game.clan.name + 'Clan')
        self.last_screen = last_screen
        self.pick_path_message = UITextBoxTweaked(
            f"What will you do now?",
            scale(pygame.Rect((40, 40), (670, -1))),
            line_spacing=1,
            object_id="#text_box_30_horizcenter",
            container=self
        )

        self.begin_anew_button = UIImageButton(
            scale(pygame.Rect((130, 140), (150, 150))),
            "",
            object_id="#random_dice_button",
            container=self,
            tool_tip_text='Start a new Clan'
        )
        
        self.mediator_button = UIImageButton(
            scale(pygame.Rect((310, 140), (150, 150))),
            "",
            object_id="#unknown_residence_button",
            container=self,
            tool_tip_text='Be reborn'

        )
        
        self.mediator_button2 = UIImageButton(
            scale(pygame.Rect((490, 140), (150, 150))),
            "",
            object_id="#leader_ceremony_button",
            container=self,
            tool_tip_text='Revive'
        )

        self.mediator_button3 = UIImageButton(
            scale(pygame.Rect((130, 330), (498, 96))),
            "",
            object_id="#continue_dead_button",
            container=self,
        )
        

        self.begin_anew_button.enable()
        self.mediator_button.enable()
        if game.clan.your_cat.revives < 5:
            self.mediator_button2.enable()
        self.mediator_button3.enable()

    def process_event(self, event):
        super().process_event(event)

        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            if event.ui_element == self.begin_anew_button:
                game.last_screen_forupdate = None
                game.switches['window_open'] = False
                game.switches['cur_screen'] = 'start screen'
                game.switches['continue_after_death'] = False
                self.begin_anew_button.kill()
                self.pick_path_message.kill()
                self.mediator_button.kill()
                self.mediator_button2.kill()
                self.mediator_button3.kill()
                self.kill()
                game.all_screens['events screen'].exit_screen()
            elif event.ui_element == self.mediator_button:
                game.last_screen_forupdate = None
                game.switches['window_open'] = False
                game.switches['cur_screen'] = "choose reborn screen"
                game.switches['continue_after_death'] = False
                self.begin_anew_button.kill()
                self.pick_path_message.kill()
                self.mediator_button.kill()
                self.mediator_button2.kill()
                self.mediator_button3.kill()
                self.kill()
                game.all_screens['events screen'].exit_screen()
            elif event.ui_element == self.mediator_button2:
                game.clan.your_cat.revives +=1
                game.clan.your_cat.dead = False
                game.clan.your_cat.df = False
                game.clan.your_cat.outside = False
                game.clan.your_cat.dead_for = 0
                game.clan.your_cat.moons+=1
                game.clan.your_cat.update_mentor()
                game.switches['continue_after_death'] = False
                if game.clan.your_cat.outside:
                    game.clan.add_to_clan(game.clan.your_cat)
                if game.clan.your_cat.ID in game.clan.starclan_cats:
                    game.clan.starclan_cats.remove(game.clan.your_cat.ID)
                if game.clan.your_cat.ID in game.clan.darkforest_cats:
                    game.clan.darkforest_cats.remove(game.clan.your_cat.ID)
                if game.clan.your_cat.ID in game.clan.unknown_cats:
                    game.clan.unknown_cats.remove(game.clan.your_cat.ID)
                you = game.clan.your_cat
                
                if you.moons == 0 and you.status != "newborn":
                    you.status = 'newborn'
                elif you.moons < 6 and you.status != "kitten":
                    you.status = "kitten"
                elif you.moons >= 6 and you.status == "kitten":
                    you.status = "apprentice"
                    you.name.status = "apprentice"

                game.clan.your_cat.thought = "Is surprised to find themselves back in the Clan"
                game.last_screen_forupdate = None
                game.switches['window_open'] = False
                with open("resources/dicts/events/lifegen_events/revival.json", "r") as read_file:
                    revival_json = ujson.loads(read_file.read())['revival']
                
                game.next_events_list.append(Single_Event(choice(revival_json), 'alert'))
                game.switches['cur_screen'] = "events screen"
                self.begin_anew_button.kill()
                self.pick_path_message.kill()
                self.mediator_button.kill()
                self.mediator_button2.kill()
                self.mediator_button3.kill()
                self.kill()
            elif event.ui_element == self.mediator_button3:
                game.last_screen_forupdate = None
                game.switches['window_open'] = False
                game.switches['cur_screen'] = "events screen"
                game.switches['continue_after_death'] = True
                self.begin_anew_button.kill()
                self.pick_path_message.kill()
                self.mediator_button.kill()
                self.mediator_button2.kill()
                self.mediator_button3.kill()
                self.kill()
                
class DeputyScreen(UIWindow):
    def __init__(self, last_screen):
        super().__init__(scale(pygame.Rect((500, 400), (600, 500))),
                         window_display_title='Choose your deputy',
                         object_id='#game_over_window',
                         resizable=False)
        self.set_blocking(True)
        game.switches['window_open'] = True
        self.clan_name = str(game.clan.name + 'Clan')
        self.last_screen = last_screen
        self.pick_path_message = UITextBoxTweaked(
            f"Choose your deputy",
            scale(pygame.Rect((40, 40), (500, -1))),
            line_spacing=1,
            object_id="#text_box_30_horizcenter",
            container=self
        )

        self.begin_anew_button = UIImageButton(
            scale(pygame.Rect((130, 190), (150, 150))),
            "",
            object_id="#random_dice_button",
            container=self,
            tool_tip_text='Skip'
        )
        
        self.mediator_button = UIImageButton(
            scale(pygame.Rect((310, 190), (150, 150))),
            "",
            object_id="#unknown_residence_button",
            container=self,
            tool_tip_text='Choose deputy'

        )

        
        self.begin_anew_button.enable()
        self.mediator_button.enable()


    def process_event(self, event):
        super().process_event(event)
        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            if event.ui_element == self.begin_anew_button:
                game.last_screen_forupdate = None
                game.switches['window_open'] = False
                self.begin_anew_button.kill()
                self.pick_path_message.kill()
                self.mediator_button.kill()
                self.kill()
            elif event.ui_element == self.mediator_button:
                game.last_screen_forupdate = None
                if game.clan.deputy:
                    game.clan.deputy.status_change('warrior')
                game.switches['window_open'] = False
                game.switches['cur_screen'] = "deputy screen"
                self.begin_anew_button.kill()
                self.pick_path_message.kill()
                self.mediator_button.kill()
                self.kill()
                game.all_screens['events screen'].exit_screen()
                
class NameKitsWindow(UIWindow):
    def __init__(self, last_screen):
        super().__init__(scale(pygame.Rect((500, 400), (600, 500))),
                         window_display_title='Name Kits',
                         object_id='#game_over_window',
                         resizable=False)
        self.set_blocking(True)
        game.switches['window_open'] = True
        self.clan_name = str(game.clan.name + 'Clan')
        self.last_screen = last_screen
        self.pick_path_message = UITextBoxTweaked(
            f"Name your kits",
            scale(pygame.Rect((40, 40), (500, -1))),
            line_spacing=1,
            object_id="#text_box_30_horizcenter",
            container=self
        )

        self.begin_anew_button = UIImageButton(
            scale(pygame.Rect((130, 190), (150, 150))),
            "",
            object_id="#random_dice_button",
            container=self,
            tool_tip_text='Randomize names'
        )
        
        self.mediator_button = UIImageButton(
            scale(pygame.Rect((310, 190), (150, 150))),
            "",
            object_id="#unknown_residence_button",
            container=self,
            tool_tip_text='Choose names'

        )

        
        self.begin_anew_button.enable()
        self.mediator_button.enable()


    def process_event(self, event):
        super().process_event(event)
        if game.switches['window_open']:
            pass

        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            try:
                if event.ui_element == self.begin_anew_button:
                    game.last_screen_forupdate = None
                    game.switches['window_open'] = False
                    self.begin_anew_button.kill()
                    self.pick_path_message.kill()
                    self.mediator_button.kill()
                    self.kill()
                elif event.ui_element == self.mediator_button:
                    game.last_screen_forupdate = None
                    game.switches['window_open'] = False
                    game.switches['cur_screen'] = "name kits screen"
                    self.begin_anew_button.kill()
                    self.pick_path_message.kill()
                    self.mediator_button.kill()
                    self.kill()
                    game.all_screens['events screen'].exit_screen()
            except:
                print("failure with kits window")

                
class MateScreen(UIWindow):
    def __init__(self, last_screen):
        super().__init__(scale(pygame.Rect((500, 400), (600, 500))),
                         window_display_title='Choose your mate',
                         object_id='#game_over_window',
                         resizable=False)
        self.set_blocking(True)
        game.switches['window_open'] = True
        self.clan_name = str(game.clan.name + 'Clan')
        self.last_screen = last_screen
        self.mate = game.switches['new_mate']
        self.pick_path_message = UITextBoxTweaked(
            f"{self.mate.name} confesses their feelings to you.",
            scale(pygame.Rect((40, 40), (520, -1))),
            line_spacing=1,
            object_id="#text_box_30_horizcenter",
            container=self
        )

        self.begin_anew_button = UIImageButton(
            scale(pygame.Rect((130, 190), (150, 150))),
            "",
            object_id="#your_clan_button",
            container=self,
            tool_tip_text='Accept and become mates'
        )
        
        self.mediator_button = UIImageButton(
            scale(pygame.Rect((310, 190), (150, 150))),
            "",
            object_id="#outside_clan_button",
            container=self,
            tool_tip_text='Reject'

        )
        

        self.begin_anew_button.enable()
        self.mediator_button.enable()



    def process_event(self, event):
        super().process_event(event)
        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            try:
                if event.ui_element == self.begin_anew_button:
                    game.last_screen_forupdate = None
                    game.switches['window_open'] = False
                    # game.switch_screens = True                    
                    self.begin_anew_button.kill()
                    self.pick_path_message.kill()
                    self.mediator_button.kill()
                    self.kill()
                    game.clan.your_cat.set_mate(game.switches['new_mate'])
                    game.switches['accept'] = True

                elif event.ui_element == self.mediator_button:
                    game.last_screen_forupdate = None
                    game.switches['window_open'] = False
                    # game.switch_screens = True
                    self.begin_anew_button.kill()
                    self.pick_path_message.kill()
                    self.mediator_button.kill()
                    self.kill()
                    game.switches['new_mate'].relationships[game.clan.your_cat.ID].romantic_love = 0
                    game.clan.your_cat.relationships[game.switches['new_mate'].ID].comfortable -= 10
                    game.switches['reject'] = True
            except:
                print("error with mate screen")

class RetireScreen(UIWindow):
    def __init__(self, last_screen):
        super().__init__(scale(pygame.Rect((500, 400), (600, 500))),
                         window_display_title='Choose to retire',
                         object_id='#game_over_window',
                         resizable=False)
        self.set_blocking(True)
        game.switches['window_open'] = True
        self.clan_name = str(game.clan.name + 'Clan')
        self.last_screen = last_screen
        game.switches['retire'] = False
        game.switches['retire_reject'] = False
        self.pick_path_message = UITextBoxTweaked(
            f"You're asked if you would like to retire",
            scale(pygame.Rect((40, 40), (520, -1))),
            line_spacing=1,
            object_id="#text_box_30_horizcenter",
            container=self
        )

        self.begin_anew_button = UIImageButton(
            scale(pygame.Rect((130, 190), (150, 150))),
            "",
            object_id="#your_clan_button",
            container=self,
            tool_tip_text='Accept and become an elder'
        )
        
        self.mediator_button = UIImageButton(
            scale(pygame.Rect((310, 190), (150, 150))),
            "",
            object_id="#outside_clan_button",
            container=self,
            tool_tip_text='Reject'

        )
        
        self.begin_anew_button.enable()
        self.mediator_button.enable()



    def process_event(self, event):
        super().process_event(event)

        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            try:
                if event.ui_element == self.begin_anew_button:
                    game.last_screen_forupdate = None
                    game.switches['window_open'] = False
                    # game.switch_screens = True                    
                    self.begin_anew_button.kill()
                    self.pick_path_message.kill()
                    self.mediator_button.kill()
                    self.kill()
                    game.switches['retire'] = True
                    game.clan.your_cat.status_change('elder')
                elif event.ui_element == self.mediator_button:
                    game.last_screen_forupdate = None
                    game.switches['window_open'] = False
                    # game.switch_screens = True
                    self.begin_anew_button.kill()
                    self.pick_path_message.kill()
                    self.mediator_button.kill()
                    self.kill()
                    game.switches['retire_reject'] = True
            except:
                print("error with retire screen")

class ChangeCatToggles(UIWindow):
    """This window allows the user to edit various cat behavior toggles"""

    def __init__(self, cat):
        super().__init__(scale(pygame.Rect((600, 430), (800, 370))),
                         window_display_title='Change Cat Name',
                         object_id='#change_cat_name_window',
                         resizable=False)
        game.switches['window_open'] = True
        self.the_cat = cat
        self.set_blocking(True)
        self.back_button = UIImageButton(
            scale(pygame.Rect((740, 10), (44, 44))),
            "",
            object_id="#exit_window_button",
            container=self
        )

        self.checkboxes = {}
        self.refresh_checkboxes()
        
        # Text
        self.text_1 = pygame_gui.elements.UITextBox("Prevent fading", scale(pygame.Rect(110, 60, -1, 50)), 
                                                    object_id="#text_box_30_horizleft_pad_0_8",
                                                    container=self)
        
        self.text_2 = pygame_gui.elements.UITextBox("Prevent kits", scale(pygame.Rect(110, 110, -1, 50)), 
                                                    object_id="#text_box_30_horizleft_pad_0_8",
                                                    container=self)
        
        self.text_3 = pygame_gui.elements.UITextBox("Prevent retirement", scale(pygame.Rect(110, 160, -1, 50)), 
                                                    object_id="#text_box_30_horizleft_pad_0_8",
                                                    container=self)
        
        self.text_4 = pygame_gui.elements.UITextBox("Limit romantic interactions and mate changes",
                                                    scale(pygame.Rect(110, 210, -1, 50)), 
                                                    object_id="#text_box_30_horizleft_pad_0_8",
                                                    container=self)
        
        # Text
        
    def refresh_checkboxes(self):
        
        for x in self.checkboxes.values():
            x.kill()
        self.checkboxes = {}
        
        # Prevent Fading
        if self.the_cat == game.clan.instructor or self.the_cat == game.clan.demon:
            box_type = "#checked_checkbox"
            tool_tip = "The afterlife guide can never fade."
        elif self.the_cat.prevent_fading:
            box_type = "#checked_checkbox"
            tool_tip = "Prevents cat from fading away after being dead for 202 moons."
        else:
            box_type = "#unchecked_checkbox"
            tool_tip = "Prevents cat from fading away after being dead for 202 moons."
        
        # Fading
        self.checkboxes["prevent_fading"] = UIImageButton(scale(pygame.Rect(45, 50, 68, 68)), "",
                                                          container=self,
                                                          object_id=box_type,
                                                          tool_tip_text=tool_tip)
        
        if self.the_cat == game.clan.instructor or self.the_cat == game.clan.demon:
            self.checkboxes["prevent_fading"].disable()
        
        
        #No Kits
        if self.the_cat.no_kits:
            box_type = "#checked_checkbox"
            tool_tip = "Prevent the cat from adopting or having kittens."
        else:
            box_type = "#unchecked_checkbox"
            tool_tip = "Prevent the cat from adopting or having kittens."
        
        self.checkboxes["prevent_kits"] = UIImageButton(scale(pygame.Rect(45, 100, 68, 68)), "",
                                                        container=self,
                                                        object_id=box_type,
                                                        tool_tip_text=tool_tip)
        
        #No Retire
        if self.the_cat.no_retire:
            box_type = "#checked_checkbox"
            tool_tip = "Allow cat to retiring automatically."
        else:
            box_type = "#unchecked_checkbox"
            tool_tip = "Prevent cat from retiring automatically."
        
        self.checkboxes["prevent_retire"] = UIImageButton(scale(pygame.Rect(45, 150, 68, 68)), "",
                                                          container=self,
                                                          object_id=box_type,
                                                          tool_tip_text=tool_tip)
        
        #No mates
        if self.the_cat.no_mates:
            box_type = "#checked_checkbox"
            tool_tip = "Prevent cat from automatically taking a mate, breaking up, or having romantic interactions with non-mates."
        else:
            box_type = "#unchecked_checkbox"
            tool_tip = "Prevent cat from automatically taking a mate, breaking up, or having romantic interactions with non-mates."
        
        self.checkboxes["prevent_mates"] = UIImageButton(scale(pygame.Rect(45, 200, 68, 68)), "",
                                                         container=self,
                                                         object_id=box_type,
                                                         tool_tip_text=tool_tip)

    def process_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            if event.ui_element == self.back_button:
                game.switches['window_open'] = False
                game.all_screens['profile screen'].exit_screen()
                game.all_screens['profile screen'].screen_switches()
                self.kill()
            elif event.ui_element == self.checkboxes["prevent_fading"]:
                self.the_cat.prevent_fading = not self.the_cat.prevent_fading
                self.refresh_checkboxes()
            elif event.ui_element == self.checkboxes["prevent_kits"]:
                self.the_cat.no_kits = not self.the_cat.no_kits
                self.refresh_checkboxes()
            elif event.ui_element == self.checkboxes["prevent_retire"]:
                self.the_cat.no_retire = not self.the_cat.no_retire
                self.refresh_checkboxes()
            elif event.ui_element == self.checkboxes["prevent_mates"]:
                self.the_cat.no_mates = not self.the_cat.no_mates
                self.refresh_checkboxes()
        
        return super().process_event(event)
