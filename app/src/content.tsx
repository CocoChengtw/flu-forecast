// Recommended actions per audience and signal level. Every action carries one
// number from this week's data, the forecast or past seasons, and each
// audience gets numbers about its own decision:
//   hospitals      lead time, peak load, peak timing
//   public health  state spread, fastest-rising state, time before the earliest surge
//   clinics        flu test positivity, demand vs. normal
//   individuals    odds that a doctor visit is flu, vaccination deadline
// The only fixed figures are CDC guidance: flu shots take about 2 weeks to
// protect, and antivirals work best within 48 hours of symptoms.

import {
  Bed, Bell, CalendarCheck, ChatCircleText, ClipboardText, Desktop, FirstAidKit, House,
  Megaphone, Package, Phone, Pill, ShieldCheck, Stethoscope, Syringe, TestTube, UsersThree,
  Buildings, Hospital, Storefront, HouseLine, Users, Thermometer, MapPin, CalendarStar,
} from "@phosphor-icons/react";
import type { Icon } from "@phosphor-icons/react";
import { addWeeks, fmtDay, pct, STATE_NAMES, type Dashboard } from "./data";

export type Action = { icon: Icon; title: string; figure: string; figureLabel: string; detail: string };
export type Audience = { id: string; label: string; icon: Icon; actions: Action[] };

export function buildAudiences(d: Dashboard): Audience[] {
  const s = d.stats;
  const lvl = d.now.level;
  const chance = d.now.chance ? pct(d.now.chance[d.now.chance.length - 1]) : "Above";
  const byDate = fmtDay(d.forecast.dates[d.forecast.dates.length - 1]);

  // Hospitals
  const lead = s.leadMin !== null ? `${s.leadMin} to ${s.leadMax} wks` : `${s.weeksToTypical} wks`;
  const leadFrom = fmtDay(addWeeks(d.updated, s.leadMin ?? s.weeksToTypical));
  const peakLoad = `${Math.round(s.medianPeak / Math.max(d.now.value, 0.1))}x`;
  const peakDate = fmtDay(s.peakDate);
  const weeksLeft = `${Math.max(s.medianWeeksAbove - s.weeksAboveSoFar, 1)} wks`;
  // Public health
  const spread = `${s.statesAbove} of ${s.statesTotal}`;
  const riser = s.topRiser ? STATE_NAMES[s.topRiser.state] ?? s.topRiser.state : null;
  const riserFig = s.topRiser ? `+${s.topRiser.change.toFixed(1)}` : "None";
  const earliestIn = `${s.weeksToEarliest} wks`;
  // Clinics
  const posNow = `${s.posNow}%`;
  const posRise = `${Math.round(s.posPeak / Math.max(s.posNow, 1))}x`;
  const vsNormal = s.vsNormal !== null ? `${s.vsNormal}x` : "Normal";
  // Individuals
  const shotBy = fmtDay(addWeeks(s.earliestCrossing, -2));
  const oddsNow = d.now.oneIn ? `1 in ${d.now.oneIn.toLocaleString()}` : "Very low";
  const oddsPeak = s.oneInPeak ? `1 in ${s.oneInPeak}` : "high";

  const A = (icon: Icon, title: string, figure: string, figureLabel: string, detail: string): Action =>
    ({ icon, title, figure, figureLabel, detail });

  const hospitals: Action[][] = [
    [
      A(ClipboardText, "Review the surge plan", `${s.medianWeeksAbove} wks`, "typical surge length", "Plan staff and beds for that many weeks above the line."),
      A(Package, "Check supplies", `${s.medianPeak}`, "flu visits per 1,000 at a typical peak", "Size test and antiviral stock to a peak near that level."),
      A(CalendarStar, "Mark the peak window", peakDate, "typical peak week", `Peaks come about ${s.lagToPeak} weeks after a surge starts.`),
    ],
    [
      A(UsersThree, "Line up extra shifts", lead, "from this level to a surge, past seasons", `Confirm who can cover extra shifts from ${leadFrom}.`),
      A(Package, "Order supplies early", peakLoad, "today's flu load at a typical peak", `Stock for a ${s.medianWeeksAbove}-week surge.`),
      A(CalendarStar, "Plan for the peak", peakDate, "typical peak week if the surge starts on time", `Peaks come about ${s.lagToPeak} weeks after a surge starts.`),
    ],
    [
      A(CalendarCheck, "Book surge staffing", chance, `chance of a surge by ${byDate}`, "Schedule extra shifts for the next 4 to 6 weeks."),
      A(Bed, "Plan to free beds", `${s.lagToPeak} wks`, "from surge start to peak, typically", "List elective procedures that can move in that window."),
      A(ShieldCheck, "Ready infection control", peakLoad, "today's flu load at a typical peak", "Have visitor limits and masking ready to switch on."),
    ],
    [
      A(Bed, "Open overflow capacity", weeksLeft, "likely left above the line", `Week ${s.weeksAboveSoFar} of a typical ${s.medianWeeksAbove}-week surge.`),
      A(CalendarStar, "Staff for the peak", peakDate, "typical peak week", "Hold extra shifts through that week."),
      A(Pill, "Prioritize antivirals", "48 hrs", "when antivirals work best", "Treat high-risk patients first."),
    ],
  ];

  const publicHealth: Action[][] = [
    [
      A(Syringe, "Run vaccine campaigns", earliestIn, "until the earliest surge start since 2016", "Reach high-risk groups at least 2 weeks before then."),
      A(Desktop, "Check reporting", `${s.statesTotal} states`, "reporting flu data this month", "Follow up with states that aren't sending data."),
      A(HouseLine, "Coordinate plans", `${s.seasonsCrossed} of ${s.seasonsTotal}`, "recent seasons crossed the surge line", "Agree surge roles with local hospitals."),
    ],
    [
      A(Megaphone, "Push vaccine messaging", earliestIn, "until the earliest surge start since 2016", "Shots take about 2 weeks to protect, so campaign now."),
      A(Bell, "Alert providers", spread, "states above the national level", "Send a flu-season advisory: test and treat early."),
      A(MapPin, riser ? `Watch ${riser}` : "Watch hot spots", riserFig, "per 1,000 in 3 weeks, the fastest rise", "Check nursing homes and schools there first."),
    ],
    [
      A(Megaphone, "Issue a health advisory", spread, "states above the national level", "Tell providers to test and treat early."),
      A(MapPin, riser ? `Support ${riser}` : "Support hot spots", riserFig, "per 1,000 in 3 weeks, the fastest rise", "Offer outbreak help where flu is climbing fastest."),
      A(Phone, "Start weekly bed calls", `${s.lagToPeak} wks`, "from surge start to peak, typically", "Track hospital capacity together through the peak."),
    ],
    [
      A(Megaphone, "Guide the public", weeksLeft, "likely left above the line", "When to stay home and when to seek care."),
      A(FirstAidKit, "Support outbreaks", spread, "states above the national level", "Help nursing homes and schools respond."),
      A(Phone, "Coordinate capacity", peakDate, "typical peak week", "Plan patient transfers between hospitals around it."),
    ],
  ];

  const clinics: Action[][] = [
    [
      A(Syringe, "Stock vaccines", fmtDay(s.earliestCrossing), "earliest surge start since 2016", "Plan walk-in flu-shot hours before then."),
      A(TestTube, "Check test kits", `${s.posPeak}%`, "of flu tests positive at a typical peak", "Plan rapid-test stock for that demand."),
      A(ChatCircleText, "Remind patients", "2 wks", "for a flu shot to protect", "Send flu-shot reminders to high-risk patients."),
    ],
    [
      A(TestTube, "Test flu symptoms", posNow, "of flu tests positive this week", `Typically ${s.posPeak}% at the peak. Test fever and cough.`),
      A(Pill, "Stock antivirals", posRise, "more positive tests at a typical peak", "Order before shortages start."),
      A(CalendarCheck, "Hold sick-visit slots", vsNormal, "flu visits vs. normal for this week", "Keep same-day appointments open."),
    ],
    [
      A(CalendarCheck, "Expand sick visits", posNow, "of flu tests positive this week", "Add same-day slots and evening hours."),
      A(Pill, "Treat early", "48 hrs", "when antivirals work best", "Start antivirals fast for high-risk patients."),
      A(Phone, "Triage by phone", vsNormal, "flu visits vs. normal for this week", "Keep mild cases out of crowded waiting rooms."),
    ],
    [
      A(Stethoscope, "Same-day treatment", "48 hrs", "when antivirals work best", "Fast antiviral access for high-risk patients."),
      A(TestTube, "Test and treat", posNow, "of flu tests positive this week", "A positive test is likely; treat high-risk patients fast."),
      A(Desktop, "Use telehealth", weeksLeft, "likely left above the line", "Handle mild cases remotely."),
    ],
  ];

  const individuals: Action[][] = [
    [
      A(Syringe, "Get a flu shot", `By ${shotBy}`, "to be protected before the earliest surge", "Shots take about 2 weeks to protect."),
      A(Phone, "Plan who to call", "48 hrs", "when antivirals work best", "If you're 65+, pregnant or have a chronic illness."),
      A(House, "Stock home basics", `${s.medianWeeksAbove} wks`, "a typical surge lasts", "Fever reducer, home tests and tissues."),
    ],
    [
      A(Syringe, "Get your flu shot now", `By ${shotBy}`, "to be protected before the earliest surge", "Shots take about 2 weeks to protect."),
      A(House, "Stay home when sick", oddsNow, "doctor visits are flu now", `About ${oddsPeak} at a typical peak.`),
      A(Phone, "Call early if high-risk", "48 hrs", "when antivirals work best", "65+, pregnant or a chronic illness: call at first symptoms."),
    ],
    [
      A(Syringe, "Get vaccinated this week", chance, `chance of a surge by ${byDate}`, "Protection takes about 2 weeks to build."),
      A(Users, "Mask in crowds", oddsNow, "doctor visits are flu now", `About ${oddsPeak} at a typical peak.`),
      A(Phone, "Call early if high-risk", "48 hrs", "when antivirals work best", "65+, pregnant or a chronic illness: call at first symptoms."),
    ],
    [
      A(House, "Stay home when sick", oddsNow, "doctor visits are flu now", "Until 24 hours without fever."),
      A(Users, "Mask in crowds", weeksLeft, "likely left above the line", "Crowded indoor places, especially near older relatives."),
      A(Thermometer, "Seek care early", "48 hrs", "when antivirals work best", "Go to the ER for trouble breathing or chest pain."),
    ],
  ];

  return [
    { id: "hospital", label: "Hospitals", icon: Hospital, actions: hospitals[lvl] },
    { id: "public-health", label: "Public health", icon: Buildings, actions: publicHealth[lvl] },
    { id: "clinics", label: "Clinics and pharmacies", icon: Storefront, actions: clinics[lvl] },
    { id: "individuals", label: "Individuals and families", icon: Users, actions: individuals[lvl] },
  ];
}

// What moves the signal to the next level, shown under the actions.
export const NEXT_STEP = [
  "Moves to Elevated when flu rises above summer levels.",
  "Moves to Surge watch at a 50% chance of crossing the surge line within 4 weeks.",
  "Moves to Surge once flu is above the surge line.",
  "Steps down after 2 weeks in a row below the surge line.",
];

export const HEADLINES = [
  "Flu is at summer levels.",
  "Flu season has started. A surge in the next 4 weeks is unlikely.",
  "A surge is likely within 4 weeks.",
  "Flu is above the surge line.",
];
