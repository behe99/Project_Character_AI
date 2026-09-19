/**
 * Single source of truth for every tunable number in the game.
 * Every system reads from here — never hardcode a balance number inline.
 * Values below are the starting points from the design doc (Section 27.1);
 * adjust them as playtesting tells you to, in this file only.
 */
export const GAME_CONSTANTS = {
  combat: {
    tickIntervalSeconds: 60,
    ambulanceArrivalMinMinutes: 3,
    ambulanceArrivalMaxMinutes: 5,
    surrenderOfferCooldownTicks: 3,
    itemForfeitPercentOnLoss: 0.5,
    gearAdvantageWinRateMin: 0.70,
    gearAdvantageWinRateMax: 0.75,
  },

  economy: {
    wholesaleMarginMin: 0.55, // wholesale price as a fraction of retail
    wholesaleMarginMax: 0.70,
  },

  police: {
    officerFineShareMin: 0.60, // fraction of the fine that goes to the arresting officer
    officerFineShareMax: 0.70,
  },

  accounts: {
    newAccountProtectionHours: 72,
  },

  stats: {
    decayStartsAtLevel: 4,
  },

  reputation: {
    meaningfulWeightDays: 30, // record still carries full mechanical weight
    fadedWeightDays: 90, // record has faded to near-zero mechanical weight
  },

  world: {
    offlineBodyPersistenceHours: 12, // in-game hours a logged-out player's body persists
  },
} as const;
