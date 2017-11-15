from flask_login import UserMixin, AnonymousUserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.ext.hybrid import hybrid_property
from app.shared import db
import datetime


class CRUD_MixIn():
    def add(self, resource):
        db.session.add(resource)
        return db.session.commit()

    def update(self):
        return db.session.commit()

    def delete(self, resource):
        db.session.delete(resource)
        return db.session.commit()


def get_or_create(session, model, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        session.commit()
        return instance


# many to many relationship between User and Team
association = db.Table('association',
                  db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
                  db.Column('team_id', db.Integer, db.ForeignKey('team.id')))


class User(db.Model, CRUD_MixIn, UserMixin):
    id = db.Column(db.Integer(), primary_key=True)
    username = db.Column(db.String(), nullable=False)
    password = db.Column(db.String(), nullable=False)
    email = db.Column(db.String())
    team = db.relationship('Team', secondary=association,
                           backref=db.backref('teams', lazy='dynamic'))

    def __init__(self, username, password):
        self.username = username
        self.set_password(password)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, value):
        return check_password_hash(self.password, value)

    @property
    def is_authenticated(self):
        if isinstance(self, AnonymousUserMixin):
            return False
        else:
            return True

    def is_active(self):
        return True

    def is_anonymous(self):
        if isinstance(self, AnonymousUserMixin):
            return True
        else:
            return False

    def get_id(self):
        return self.id

    def __repr__(self):
        return '<User {}>'.format(self.username)


class Team(db.Model, CRUD_MixIn):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(), nullable=False)

    # relationships
    matches = db.relationship('Match', back_populates="team")
    players = db.relationship("Player", back_populates="team")

    def __init__(self, name=None):
        self.name = name

    def __repr__(self):
        return "Team (name={})".format(self.name)


class Opponent(db.Model, CRUD_MixIn):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    coach_name = db.Column(db.String())
    team_crest_uri = db.Column(db.String())
    external_url = db.Column(db.String())

    # relationships
    matches = db.relationship("Match", back_populates="opponent")

    @hybrid_property
    def num_match_won(self):
        """ return competition result in W-D-L format """
        return len([i for i in self.matches if (i.result == "win")])

    @hybrid_property
    def num_match_tied(self):
        """ return competition result in W-D-L format """
        return len([i for i in self.matches if (i.result == "tie")])

    @hybrid_property
    def num_match_lost(self):
        """ return competition result in W-D-L format """
        return len([i for i in self.matches if (i.result == "loss")])

    @hybrid_property
    def match_results(self):
        """ return competition result in W-D-L format """
        return "{}-{}-{}".format(self.num_match_won,
                                 self.num_match_tied,
                                 self.num_match_lost)

    def __init__(self, name, coach_name=None, external_url=None):
        self.name = name
        self.coach_name = coach_name
        self.external_url = external_url

    def __repr__(self):
        return "Opponent (name={})".format(self.name)


class Competition(db.Model, CRUD_MixIn):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    result = db.Column(db.String())
    external_url = db.Column(db.String())

    # relationships
    matches = db.relationship("Match", back_populates="competition")

    @hybrid_property
    def num_match_won(self):
        """ return competition result in W-D-L format """
        return len([i for i in self.matches if (i.result == "win")])

    @hybrid_property
    def num_match_tied(self):
        """ return competition result in W-D-L format """
        return len([i for i in self.matches if (i.result == "tie")])

    @hybrid_property
    def num_match_lost(self):
        """ return competition result in W-D-L format """
        return len([i for i in self.matches if (i.result == "loss")])

    @hybrid_property
    def match_results(self):
        """ return competition result in W-D-L format """
        return "{}-{}-{}".format(self.num_match_won,
                                 self.num_match_tied,
                                 self.num_match_lost)

    def __init__(self, name, result=None, external_url=None):
        self.name = name
        self.result = result
        self.external_url = external_url

    def __repr__(self):
        return "Competition (name={})".format(self.name)


class Match(db.Model, CRUD_MixIn):
    id = db.Column(db.Integer(), primary_key=True)
    date_time = db.Column(db.DateTime(), nullable=False, index=True)
    at_home = db.Column(db.Boolean())
    duration = db.Column(db.Integer())  # match duration in minutes

    # relationships
    player_matches = db.relationship("PlayerMatch", back_populates="match",
                                     cascade="all, delete-orphan")

    team_id = db.Column(db.Integer, db.ForeignKey('team.id'),
                        nullable=False, index=True)
    team = db.relationship("Team", back_populates="matches")

    opponent_id = db.Column(db.Integer, db.ForeignKey('opponent.id'),
                            nullable=False, index=True)
    opponent = db.relationship("Opponent", back_populates="matches")

    competition_id = db.Column(db.Integer, db.ForeignKey('competition.id'),
                               index=True)
    competition = db.relationship("Competition", back_populates="matches")

    match_stats = db.relationship("MatchStats",
                                  uselist=False,
                                  back_populates="match",
                                  cascade="all, delete-orphan")

    @hybrid_property
    def result(self):
        goals_for = self.num_goals
        goals_against = self.num_goals_against

        if goals_for > goals_against:
            result = "win"
        elif goals_for < goals_against:
            result = "loss"
        else:
            result = "tie"

        return result

    @hybrid_property
    def result_long(self):
        return "{}-{} {}".format(self.num_goals,
                                 self.num_goals_against,
                                 self.result)

    @hybrid_property
    def label(self):
        return "match 2 of tourney X (2017/11/5), - or something like that"

    @hybrid_property
    def num_goals(self):
        return sum([i.num_goals for i in self.player_matches])

    @hybrid_property
    def num_goals_against(self):
        return sum([i.num_goals_against for i in self.player_matches])

    @hybrid_property
    def goals_timeline(self):
        return ["1' Ghis (Joe)", "33' Ghis (Jim)"]

    @hybrid_property
    def num_shots(self):
        return sum([i.num_shots for i in self.player_matches])

    @hybrid_property
    def num_shots_on_target(self):
        return sum([i.num_shots_on_target for i in self.player_matches])

    @hybrid_property
    def num_shots_against(self):
        return sum([i.num_shots_against for i in self.player_matches])

    @hybrid_property
    def opponent_num_shots_on_target(self):
        return sum([i.num_shots_against_on_target for i in self.player_matches])

    @hybrid_property
    def shot_on_target_pct(self):
        try:
            return round(self.num_shots_on_target / self.num_shots * 100, 1)
        except ZeroDivisionError:
            return 0.0

    @hybrid_property
    def opponent_shot_on_target_pct(self):
        try:
            return round(self.opponent_num_shots_on_target /
                         self.num_shots_against * 100, 1)
        except ZeroDivisionError:
            return 0.0

    @hybrid_property
    def num_corners(self):
        return sum([i.corners for i in self.player_matches])

    @hybrid_property
    def num_opponent_corners(self):
        try:
            return self.match_stats.opponent_corners
        except:
            return

    @hybrid_property
    def num_yellow_cards(self):
        return sum([i.yellow_cards for i in self.player_matches])

    @hybrid_property
    def num_opponent_yellow_cards(self):
        try:
            return self.match_stats.opponent_yellow_cards
        except:
            return

    @hybrid_property
    def num_red_cards(self):
        return sum([i.red_cards for i in self.player_matches])

    @hybrid_property
    def num_opponent_red_cards(self):
        try:
            return self.match_stats.opponent_red_cards
        except:
            return

    @hybrid_property
    def num_passes(self):
        try:
            return self.match_stats.passes
        except:
            return

    @hybrid_property
    def num_opponent_passes(self):
        try:
            return self.match_stats.opponent_passes
        except:
            return

    @hybrid_property
    def num_pass_strings(self):
        try:
            return self.match_stats.pass_strings
        except:
            return

    @hybrid_property
    def num_opponent_pass_strings(self):
        try:
            return self.match_stats.opponent_pass_strings
        except:
            return

    @hybrid_property
    def pass_pct(self):
        try:
            return self.match_stats.pass_pct
        except:
            return

    @hybrid_property
    def opponent_pass_pct(self):
        try:
            return self.match_stats.opponent_pass_pct
        except:
            return

    def __init__(self, date_time, team, opponent, competition=None,
                 at_home=True, duration=None):
        self.date_time = datetime.datetime.strptime(date_time.split(".")[0],
                                                    "%Y-%m-%dT%H:%M:%S",)
        self.team = team
        self.opponent = opponent
        self.competition = competition
        self.at_home = at_home
        self.duration = duration

    def __repr__(self):
        return "Match (team={}, opponent={}, date_time={})".format(
                                self.team, self.opponent, self.date_time)


class MatchStats(db.Model, CRUD_MixIn):
    id = db.Column(db.Integer(), primary_key=True)

    passes = db.Column(db.Integer())
    pass_strings = db.Column(db.Integer())
    pass_pct = db.Column(db.Integer())
    possession = db.Column(db.Integer())

    opponent_passes = db.Column(db.Integer())
    opponent_pass_strings = db.Column(db.Integer())
    opponent_pass_pct = db.Column(db.Integer())

    opponent_yellow_cards = db.Column(db.Integer())
    opponent_red_cards = db.Column(db.Integer())
    opponent_corners = db.Column(db.Integer())

    # relationships
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'),
                         nullable=False, index=True)
    match = db.relationship("Match", back_populates="match_stats")

    def __init__(self, match, passes=None, pass_strings=None, pass_pct=None,
                 opponent_passes=None, opponent_pass_strings=None,
                 opponent_pass_pct=None, opponent_yellow_cards=None,
                 opponent_red_cards=None, opponent_corners=None):
        self.match = match
        self.passes = passes
        self.pass_strings = pass_strings
        self.pass_pct = pass_pct
        self.opponent_passes = opponent_passes
        self.opponent_pass_strings = opponent_pass_strings
        self.opponent_pass_pct = opponent_pass_pct
        self.opponent_yellow_cards = opponent_yellow_cards
        self.opponent_red_cards = opponent_red_cards
        self.opponent_corners = opponent_corners


class Player(db.Model, CRUD_MixIn):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    number = db.Column(db.Integer())
    active = db.Column(db.Integer(), nullable=False, default=True)

    # relationships
    player_matches = db.relationship("PlayerMatch", back_populates="player")

    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    team = db.relationship("Team", back_populates="players")

    def __init__(self, name, number=None, team=None, active=True):
        self.name = name
        self.number = number
        self.team = team
        self.active = active

    def __repr__(self):
        return "Player (number={}, name={})".format(self.number, self.name)


class PlayerMatch(db.Model, CRUD_MixIn):
    __table_args__ = (db.UniqueConstraint('player_id', 'match_id'),)

    id = db.Column(db.Integer(), primary_key=True)
    starter = db.Column(db.Boolean(), default=False)
    minutes = db.Column(db.Integer(), default=0)
    subbed_due_to_injury = db.Column(db.Boolean(), default=False)
    yellow_cards = db.Column(db.Integer(), default=0)
    red_cards = db.Column(db.Integer(), default=0)
    corners = db.Column(db.Integer(), default=0)

    # relationships
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'),
                          nullable=False, index=True)
    player = db.relationship("Player", back_populates="player_matches")

    match_id = db.Column(db.Integer, db.ForeignKey('match.id'),
                         nullable=False, index=True)
    match = db.relationship("Match", back_populates="player_matches")

    shots = db.relationship("Shot", back_populates="player_match",
                            cascade="all, delete-orphan")

    # goal cascades to assist
    assists = db.relationship("Assist", back_populates="player_match")

    @hybrid_property
    def num_shots(self):
        return len([i for i in self.shots if not i.by_opponent])

    @hybrid_property
    def num_shots_against(self):
        return len([i for i in self.shots if i.by_opponent])

    @hybrid_property
    def num_shots_on_target(self):
        return len([i for i in self.shots if (not i.by_opponent and i.on_goal)])

    @hybrid_property
    def num_shots_against_on_target(self):
        return len([i for i in self.shots if (i.by_opponent and i.on_goal)])

    @hybrid_property
    def num_goals(self):
        return len([i for i in self.shots if (i.scored and not i.by_opponent)])

    @hybrid_property
    def num_goals_against(self):
        return len([i for i in self.shots if (i.scored and i.by_opponent)])

    @hybrid_property
    def num_saves(self):
        return len([i for i in self.shots if i.by_opponent])

    @hybrid_property
    def num_assists(self):
        return len(self.assists)

    def __init__(self, player, match, starter=True, minutes=0,
                 subbed_due_to_injury=None,
                 yellow_cards=None, red_cards=None, corners=None,):
        self.player = player
        self.match = match
        self.starter = starter
        self.minutes = minutes
        self.subbed_due_to_injury = subbed_due_to_injury
        self.yellow_cards = yellow_cards
        self.red_cards = red_cards
        self.corners = corners

    def __repr__(self):
        return "PlayerMatch (player={}, starter={}, minutes={})".format(
            self.player.name, self.starter, self.minutes,)


class Shot(db.Model, CRUD_MixIn):
    id = db.Column(db.Integer(), primary_key=True)
    x = db.Column(db.Integer(),)
    y = db.Column(db.Integer(),)
    on_goal = db.Column(db.Boolean(), default=False, nullable=False)
    scored = db.Column(db.Boolean(), default=False, nullable=False)
    pk = db.Column(db.Boolean(), default=False)
    by_opponent = db.Column(db.Boolean(), default=False)

    # relationships
    player_match_id = db.Column(db.Integer, db.ForeignKey('player_match.id'),
                                nullable=False, index=True)
    player_match = db.relationship("PlayerMatch", back_populates="shots")

    goal = db.relationship("Goal", uselist=False, back_populates="shot",
                           cascade="all, delete-orphan")

    def __init__(self, player_match, x=None, y=None, on_goal=None, scored=None,
                 pk=None, by_opponent=None):
        self.player_match = player_match
        self.x = x
        self.y = y
        self.on_goal = on_goal
        self.scored = scored
        self.pk = pk
        self.by_opponent = by_opponent

    def __repr__(self):
        return "Shot (player={}, x={}, y={}, on_goal={}, pk={})".format(
                        self.player_match.player.name,
                        self.x, self.y, self.on_goal,
                        self.pk, self.by_opponent)


class Goal(db.Model, CRUD_MixIn):
    id = db.Column(db.Integer(), primary_key=True)
    time = db.Column(db.Integer(), nullable=True)

    # relationships
    shot_id = db.Column(db.Integer, db.ForeignKey('shot.id'),
                        nullable=False, index=True)
    shot = db.relationship("Shot", back_populates="goal")

    assist = db.relationship("Assist", back_populates="goal", uselist=False,
                             cascade="all, delete-orphan")

    def __init__(self, shot, time=None):
        self.shot = shot
        self.time = time

    def __repr__(self):
        return "Goal (player={}, )".format(self.shot.player_match.player.name)


class Assist(db.Model, CRUD_MixIn):
    id = db.Column(db.Integer(), primary_key=True)

    # relationships
    player_match_id = db.Column(db.Integer, db.ForeignKey('player_match.id'),
                                nullable=False, index=True)
    player_match = db.relationship("PlayerMatch", back_populates="assists")

    goal_id = db.Column(db.Integer, db.ForeignKey('goal.id'),
                        nullable=False, index=True)
    goal = db.relationship("Goal", back_populates="assist")

    def __init__(self, player_match, goal):
        self.player_match = player_match
        self.goal = goal

    def __repr__(self):
        return "Assist (player={}, Goal.player={})".format(
                    self.player_match.player.name,
                    self.goal.shot.player_match.player.name)