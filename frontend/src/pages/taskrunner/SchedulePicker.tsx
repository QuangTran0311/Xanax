import { useEffect, useMemo, useState } from "react";

import { Icon } from "../../components/Icon";
import { Tooltip } from "../../components/Tooltip";
import { taskrunnerText, useTaskrunnerText, type TaskrunnerMessageKey, type TaskrunnerTranslator } from "../../i18n/taskrunner";
import { useTooltipText, type TooltipMessageKey } from "../../i18n/tooltips";
import type { Language } from "../../store/language";
import styles from "./TaskrunnerPage.module.css";

const c = (name: string) => styles[name] ?? name;

const MINUTE_INTERVALS = [5, 10, 15, 20, 30] as const;
const WEEKDAYS = [
  { value: 0, cron: "mon", shortKey: "schedule.weekday.mon.short", labelKey: "schedule.weekday.mon", tooltip: "tooltip.schedule.monday" },
  { value: 1, cron: "tue", shortKey: "schedule.weekday.tue.short", labelKey: "schedule.weekday.tue", tooltip: "tooltip.schedule.tuesday" },
  { value: 2, cron: "wed", shortKey: "schedule.weekday.wed.short", labelKey: "schedule.weekday.wed", tooltip: "tooltip.schedule.wednesday" },
  { value: 3, cron: "thu", shortKey: "schedule.weekday.thu.short", labelKey: "schedule.weekday.thu", tooltip: "tooltip.schedule.thursday" },
  { value: 4, cron: "fri", shortKey: "schedule.weekday.fri.short", labelKey: "schedule.weekday.fri", tooltip: "tooltip.schedule.friday" },
  { value: 5, cron: "sat", shortKey: "schedule.weekday.sat.short", labelKey: "schedule.weekday.sat", tooltip: "tooltip.schedule.saturday" },
  { value: 6, cron: "sun", shortKey: "schedule.weekday.sun.short", labelKey: "schedule.weekday.sun", tooltip: "tooltip.schedule.sunday" },
] as const;

type ScheduleMode = "none" | "minutes" | "hourly" | "daily" | "weekly" | "custom";

interface ScheduleState {
  mode: ScheduleMode;
  everyMinutes: number;
  hour: number;
  minute: number;
  weekdays: number[];
  raw: string;
}

const DEFAULT_STATE: ScheduleState = {
  mode: "none",
  everyMinutes: 15,
  hour: 8,
  minute: 0,
  weekdays: [0],
  raw: "",
};

const pad2 = (value: number) => String(value).padStart(2, "0");

function weekdayValue(token: string): number | null {
  const normalized = token.toLocaleLowerCase("en");
  if (/^[0-6]$/.test(normalized)) return Number(normalized);
  const named = WEEKDAYS.find((day) => day.cron === normalized);
  return named?.value ?? null;
}

function parseWeekdays(field: string): number[] | null {
  const result = new Set<number>();
  for (const part of field.split(",")) {
    const range = /^([a-z]{3}|[0-6])-([a-z]{3}|[0-6])$/i.exec(part);
    if (range) {
      const from = weekdayValue(range[1]);
      const to = weekdayValue(range[2]);
      if (from === null || to === null || from > to) return null;
      for (let day = from; day <= to; day += 1) result.add(day);
      continue;
    }
    const day = weekdayValue(part);
    if (day === null) return null;
    result.add(day);
  }
  return result.size ? [...result].sort((left, right) => left - right) : null;
}

export function parseScheduleCron(value: string | null | undefined): ScheduleState {
  const cron = String(value || "").trim();
  if (!cron) return { ...DEFAULT_STATE, weekdays: [...DEFAULT_STATE.weekdays] };
  const fields = cron.split(/\s+/);
  const custom = (): ScheduleState => ({ ...DEFAULT_STATE, weekdays: [...DEFAULT_STATE.weekdays], mode: "custom", raw: cron });
  if (fields.length !== 5) return custom();

  const [minuteField, hourField, dayField, monthField, weekdayField] = fields;
  if (dayField !== "*" || monthField !== "*") return custom();

  const interval = /^\*\/(\d+)$/.exec(minuteField);
  if (interval && hourField === "*" && weekdayField === "*") {
    const everyMinutes = Number(interval[1]);
    return MINUTE_INTERVALS.includes(everyMinutes as (typeof MINUTE_INTERVALS)[number])
      ? { ...DEFAULT_STATE, weekdays: [...DEFAULT_STATE.weekdays], mode: "minutes", everyMinutes }
      : custom();
  }

  if (!/^\d+$/.test(minuteField)) return custom();
  const minute = Number(minuteField);
  if (minute < 0 || minute > 59) return custom();
  if (hourField === "*" && weekdayField === "*") {
    return { ...DEFAULT_STATE, weekdays: [...DEFAULT_STATE.weekdays], mode: "hourly", minute };
  }

  if (!/^\d+$/.test(hourField)) return custom();
  const hour = Number(hourField);
  if (hour < 0 || hour > 23) return custom();
  if (weekdayField === "*") {
    return { ...DEFAULT_STATE, weekdays: [...DEFAULT_STATE.weekdays], mode: "daily", hour, minute };
  }

  const weekdays = parseWeekdays(weekdayField);
  return weekdays
    ? { ...DEFAULT_STATE, mode: "weekly", hour, minute, weekdays }
    : custom();
}

function buildScheduleCron(state: ScheduleState): string {
  switch (state.mode) {
    case "none": return "";
    case "minutes": return `*/${state.everyMinutes} * * * *`;
    case "hourly": return `${state.minute} * * * *`;
    case "daily": return `${state.minute} ${state.hour} * * *`;
    case "weekly": {
      /*
       * CỰC KỲ QUAN TRỌNG: backend dùng APScheduler, trong đó số 0 là Thứ Hai,
       * không phải Chủ Nhật như cron Unix. Luôn sinh tên tiếng Anh để lịch không
       * bị lệch một ngày. Phần đọc lịch cũ ở trên vẫn chấp nhận số theo đúng quy
       * ước APScheduler (0=Thứ Hai).
       */
      const names = state.weekdays.map((value) => WEEKDAYS[value]?.cron).filter(Boolean);
      return `${state.minute} ${state.hour} * * ${names.join(",")}`;
    }
    case "custom": return state.raw.trim();
  }
}

export function describeScheduleCron(value: string | null | undefined, language: Language = "vi"): string {
  const text: TaskrunnerTranslator = (key, ...args) => taskrunnerText(language, key, ...args);
  const state = parseScheduleCron(value);
  const time = `${pad2(state.hour)}:${pad2(state.minute)}`;
  switch (state.mode) {
    case "none": return text("schedule.mode.none");
    case "minutes": return text("schedule.describe.minutes", state.everyMinutes);
    case "hourly": return text("schedule.describe.hourly", pad2(state.minute));
    case "daily": return text("schedule.describe.daily", time);
    case "weekly": {
      const days = state.weekdays.map((value) => WEEKDAYS[value]?.shortKey).filter(Boolean).map((key) => text(key as TaskrunnerMessageKey)).join(", ");
      return text("schedule.describe.weekly", days, time);
    }
    case "custom": return text("schedule.mode.custom");
  }
}

function nextRunFromState(state: ScheduleState, now = new Date()): Date | null {
  if (state.mode === "none" || state.mode === "custom") return null;
  if (state.mode === "minutes") {
    const next = new Date(now);
    next.setSeconds(0, 0);
    next.setMinutes(next.getMinutes() + 1);
    while (next.getMinutes() % state.everyMinutes !== 0) next.setMinutes(next.getMinutes() + 1);
    return next;
  }
  if (state.mode === "hourly") {
    const next = new Date(now);
    next.setMinutes(state.minute, 0, 0);
    if (next <= now) next.setHours(next.getHours() + 1);
    return next;
  }
  if (state.mode === "daily") {
    const next = new Date(now);
    next.setHours(state.hour, state.minute, 0, 0);
    if (next <= now) next.setDate(next.getDate() + 1);
    return next;
  }

  for (let offset = 0; offset <= 7; offset += 1) {
    const candidate = new Date(now);
    candidate.setDate(now.getDate() + offset);
    candidate.setHours(state.hour, state.minute, 0, 0);
    const apsWeekday = (candidate.getDay() + 6) % 7;
    if (state.weekdays.includes(apsWeekday) && candidate > now) return candidate;
  }
  return null;
}

function scheduleSentence(state: ScheduleState, text: TaskrunnerTranslator): string {
  const time = `${pad2(state.hour)}:${pad2(state.minute)}`;
  switch (state.mode) {
    case "none": return text("schedule.sentence.none");
    case "minutes": return text("schedule.sentence.minutes", state.everyMinutes);
    case "hourly": return text("schedule.sentence.hourly", pad2(state.minute));
    case "daily": return text("schedule.sentence.daily", time);
    case "weekly": {
      const names = state.weekdays.map((value) => WEEKDAYS[value]?.labelKey).filter(Boolean).map((key) => text(key as TaskrunnerMessageKey)).join(", ");
      return text("schedule.sentence.weekly", time, names);
    }
    case "custom": return state.raw;
  }
}

function formatNextRun(date: Date, text: TaskrunnerTranslator): string {
  const weekdayKey = WEEKDAYS[(date.getDay() + 6) % 7]?.labelKey;
  const weekday = weekdayKey ? text(weekdayKey) : "";
  const locale = text("common.locale");
  const time = date.toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit", hour12: false });
  const dayMonth = date.toLocaleDateString(locale, { day: "numeric", month: "numeric" });
  return `${time} ${weekday}, ${dayMonth}`;
}

export function SchedulePicker({ value, onChange }: { value: string | null | undefined; onChange: (cron: string) => void }) {
  const tt = useTooltipText();
  const text = useTaskrunnerText();
  const [state, setState] = useState<ScheduleState>(() => parseScheduleCron(value));

  useEffect(() => setState(parseScheduleCron(value)), [value]);

  const nextRun = useMemo(() => nextRunFromState(state), [state]);
  const update = (next: ScheduleState) => {
    setState(next);
    onChange(buildScheduleCron(next));
  };
  const patch = (changes: Partial<ScheduleState>) => update({ ...state, ...changes });
  const changeMode = (mode: ScheduleMode) => {
    const raw = mode === "custom" && state.mode !== "custom" ? buildScheduleCron(state) : state.raw;
    update({ ...state, mode, raw });
  };
  const toggleWeekday = (weekday: number) => {
    const selected = state.weekdays.includes(weekday);
    if (selected && state.weekdays.length === 1) return;
    patch({ weekdays: selected ? state.weekdays.filter((value) => value !== weekday) : [...state.weekdays, weekday].sort() });
  };

  return <div className={c("schedule-picker")}>
    <select className={c("se-input")} value={state.mode} onChange={(event) => changeMode(event.target.value as ScheduleMode)}>
      <option value="none">{text("schedule.mode.none")}</option>
      <option value="minutes">{text("schedule.mode.minutes")}</option>
      <option value="hourly">{text("schedule.mode.hourly")}</option>
      <option value="daily">{text("schedule.mode.daily")}</option>
      <option value="weekly">{text("schedule.mode.weekly")}</option>
      <option value="custom">{text("schedule.mode.custom")}</option>
    </select>

    {state.mode === "minutes" ? <label className={c("schedule-control")}>
      <span>{text("schedule.control.interval")}</span>
      <select className={c("se-input")} value={state.everyMinutes} onChange={(event) => patch({ everyMinutes: Number(event.target.value) })}>
        {MINUTE_INTERVALS.map((minutes) => <option key={minutes} value={minutes}>{text("schedule.control.minutes", minutes)}</option>)}
      </select>
    </label> : null}

    {state.mode === "hourly" ? <label className={c("schedule-control")}>
      <span>{text("schedule.control.minute_in_hour")}</span>
      <select className={c("se-input")} value={state.minute} onChange={(event) => patch({ minute: Number(event.target.value) })}>
        {Array.from({ length: 60 }, (_, minute) => <option key={minute} value={minute}>{text("schedule.control.minute", pad2(minute))}</option>)}
      </select>
    </label> : null}

    {state.mode === "daily" || state.mode === "weekly" ? <label className={c("schedule-control")}>
      <span>{text("schedule.control.time")}</span>
      <input className={c("se-input")} type="time" value={`${pad2(state.hour)}:${pad2(state.minute)}`} onChange={(event) => {
        const [hour, minute] = event.target.value.split(":").map(Number);
        if (Number.isFinite(hour) && Number.isFinite(minute)) patch({ hour, minute });
      }} />
    </label> : null}

    {state.mode === "weekly" ? <div className={c("schedule-control")}>
      <span>{text("schedule.control.weekdays")}</span>
      <div className={c("schedule-weekdays")}>
        {WEEKDAYS.map((day) => {
          const isRequired = state.weekdays.includes(day.value) && state.weekdays.length === 1;
          const tooltip = tt(isRequired ? "tooltip.schedule.required_day" : day.tooltip as TooltipMessageKey);
          return <Tooltip key={day.cron} label={tooltip}><button
            type="button"
            className={`${c("schedule-day")} ${state.weekdays.includes(day.value) ? c("active") : ""}`}
            aria-label={tt(day.tooltip as TooltipMessageKey)}
            aria-pressed={state.weekdays.includes(day.value)}
            onClick={() => toggleWeekday(day.value)}
          >{text(day.shortKey)}</button></Tooltip>;
        })}
      </div>
    </div> : null}

    {state.mode === "custom" ? <label className={c("schedule-control")}>
      <span>{text("schedule.custom_label")}</span>
      <input className={c("se-input")} value={state.raw} placeholder="0 8 * * mon-fri" onChange={(event) => patch({ raw: event.target.value })} />
      <small>{text("schedule.custom_hint")}</small>
    </label> : <div className={c("schedule-preview")}>
      <Icon name="clock" size={14} />
      <span>{scheduleSentence(state, text)}{nextRun ? <> <strong>{text("schedule.next_run", formatNextRun(nextRun, text))}</strong></> : "."}</span>
    </div>}
  </div>;
}
