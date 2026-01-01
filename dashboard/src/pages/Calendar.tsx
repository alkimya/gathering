// Calendar page - Scheduled actions and events view

import { useState } from 'react';
import {
  Calendar as CalendarIcon,
  ChevronLeft,
  ChevronRight,
  Clock,
  Bot,
  Target,
  Play,
  RefreshCw,
  Plus,
  Filter,
} from 'lucide-react';

// Types
interface CalendarEvent {
  id: string;
  title: string;
  type: 'scheduled_action' | 'goal_deadline' | 'task_due' | 'meeting';
  date: Date;
  time?: string;
  agent_id?: string;
  agent_name?: string;
  description?: string;
  status: 'pending' | 'completed' | 'running' | 'failed';
  recurrence?: string;
}

// Configuration des couleurs par type
const eventTypeConfig = {
  scheduled_action: { color: 'bg-purple-500', textColor: 'text-purple-400', label: 'Action' },
  goal_deadline: { color: 'bg-amber-500', textColor: 'text-amber-400', label: 'Goal' },
  task_due: { color: 'bg-blue-500', textColor: 'text-blue-400', label: 'Task' },
  meeting: { color: 'bg-emerald-500', textColor: 'text-emerald-400', label: 'Meeting' },
};

// Jours et mois en français
const DAYS = ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'];
const MONTHS = [
  'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
];

// Composant pour une journée du calendrier
function CalendarDay({
  date,
  isCurrentMonth,
  isToday,
  events,
  onSelectDate,
  isSelected,
}: {
  date: Date;
  isCurrentMonth: boolean;
  isToday: boolean;
  events: CalendarEvent[];
  onSelectDate: (date: Date) => void;
  isSelected: boolean;
}) {
  const dayEvents = events.filter(
    (e) =>
      e.date.getDate() === date.getDate() &&
      e.date.getMonth() === date.getMonth() &&
      e.date.getFullYear() === date.getFullYear()
  );

  return (
    <button
      onClick={() => onSelectDate(date)}
      className={`min-h-[100px] p-2 border border-zinc-800 transition-colors ${
        isCurrentMonth ? 'bg-zinc-900/30' : 'bg-zinc-900/10'
      } ${isSelected ? 'ring-2 ring-purple-500/50 bg-purple-500/10' : ''} ${
        isToday ? 'border-purple-500/50' : ''
      } hover:bg-zinc-800/50`}
    >
      <div className="flex items-center justify-between mb-1">
        <span
          className={`text-sm font-medium ${
            isCurrentMonth ? 'text-zinc-300' : 'text-zinc-600'
          } ${isToday ? 'bg-purple-500 text-white px-2 py-0.5 rounded-full' : ''}`}
        >
          {date.getDate()}
        </span>
        {dayEvents.length > 0 && (
          <span className="text-xs text-zinc-500">{dayEvents.length}</span>
        )}
      </div>
      <div className="space-y-1">
        {dayEvents.slice(0, 3).map((event) => {
          const config = eventTypeConfig[event.type];
          return (
            <div
              key={event.id}
              className={`text-xs truncate px-1.5 py-0.5 rounded ${config.color}/20 ${config.textColor}`}
            >
              {event.time && <span className="opacity-70">{event.time} </span>}
              {event.title}
            </div>
          );
        })}
        {dayEvents.length > 3 && (
          <div className="text-xs text-zinc-500 px-1">+{dayEvents.length - 3} more</div>
        )}
      </div>
    </button>
  );
}

// Composant pour un événement dans la sidebar
function EventCard({ event }: { event: CalendarEvent }) {
  const config = eventTypeConfig[event.type];

  return (
    <div className="glass-card rounded-xl p-4 hover:bg-white/5 transition-colors">
      <div className="flex items-start gap-3">
        <div className={`w-1 h-full min-h-[40px] rounded-full ${config.color}`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-xs px-2 py-0.5 rounded-full ${config.color}/20 ${config.textColor}`}>
              {config.label}
            </span>
            {event.time && (
              <span className="text-xs text-zinc-500 flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {event.time}
              </span>
            )}
          </div>
          <h3 className="font-medium text-zinc-200 text-sm">{event.title}</h3>
          {event.description && (
            <p className="text-xs text-zinc-500 mt-1 line-clamp-2">{event.description}</p>
          )}
          <div className="flex items-center gap-3 mt-2 text-xs text-zinc-500">
            {event.agent_name && (
              <span className="flex items-center gap-1">
                <Bot className="w-3 h-3" />
                {event.agent_name}
              </span>
            )}
            {event.recurrence && (
              <span className="flex items-center gap-1">
                <RefreshCw className="w-3 h-3" />
                {event.recurrence}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1">
          {event.status === 'running' && (
            <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse" />
          )}
          {event.status === 'completed' && (
            <div className="w-2 h-2 bg-emerald-400 rounded-full" />
          )}
          {event.status === 'failed' && (
            <div className="w-2 h-2 bg-red-400 rounded-full" />
          )}
          {event.status === 'pending' && (
            <div className="w-2 h-2 bg-zinc-400 rounded-full" />
          )}
        </div>
      </div>
    </div>
  );
}

export function Calendar() {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState<Date | null>(new Date());
  const [events] = useState<CalendarEvent[]>([]);
  const [filter, setFilter] = useState<string>('all');

  // Navigation du calendrier
  const goToPreviousMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1));
  };

  const goToNextMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1));
  };

  const goToToday = () => {
    const today = new Date();
    setCurrentDate(today);
    setSelectedDate(today);
  };

  // Générer les jours du calendrier
  const generateCalendarDays = () => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();

    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);

    const days: { date: Date; isCurrentMonth: boolean }[] = [];

    // Jours du mois précédent
    const startDay = firstDay.getDay();
    for (let i = startDay - 1; i >= 0; i--) {
      days.push({
        date: new Date(year, month, -i),
        isCurrentMonth: false,
      });
    }

    // Jours du mois courant
    for (let i = 1; i <= lastDay.getDate(); i++) {
      days.push({
        date: new Date(year, month, i),
        isCurrentMonth: true,
      });
    }

    // Jours du mois suivant
    const remainingDays = 42 - days.length; // 6 semaines * 7 jours
    for (let i = 1; i <= remainingDays; i++) {
      days.push({
        date: new Date(year, month + 1, i),
        isCurrentMonth: false,
      });
    }

    return days;
  };

  const calendarDays = generateCalendarDays();
  const today = new Date();

  // Filtrer les événements
  const filteredEvents = events.filter((event) => {
    if (filter === 'all') return true;
    return event.type === filter;
  });

  // Événements de la date sélectionnée
  const selectedDateEvents = selectedDate
    ? filteredEvents.filter(
        (e) =>
          e.date.getDate() === selectedDate.getDate() &&
          e.date.getMonth() === selectedDate.getMonth() &&
          e.date.getFullYear() === selectedDate.getFullYear()
      )
    : [];

  // Événements à venir (prochains 7 jours)
  const upcomingEvents = filteredEvents
    .filter((e) => {
      const eventDate = new Date(e.date);
      const now = new Date();
      const weekFromNow = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
      return eventDate >= now && eventDate <= weekFromNow;
    })
    .sort((a, b) => a.date.getTime() - b.date.getTime());

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <CalendarIcon className="w-8 h-8 text-purple-400" />
            Calendar
          </h1>
          <p className="text-zinc-400 mt-1">
            Actions planifiées et échéances
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button className="btn-gradient px-4 py-2 rounded-xl flex items-center gap-2">
            <Plus className="w-5 h-5" />
            New Event
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2">
        <Filter className="w-4 h-4 text-zinc-500" />
        {[
          { key: 'all', label: 'Tout' },
          { key: 'scheduled_action', label: 'Actions' },
          { key: 'goal_deadline', label: 'Goals' },
          { key: 'task_due', label: 'Tasks' },
          { key: 'meeting', label: 'Meetings' },
        ].map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`px-4 py-2 rounded-lg text-sm transition-colors ${
              filter === f.key
                ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                : 'bg-zinc-800/50 text-zinc-400 hover:bg-zinc-700/50'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Calendar Grid */}
        <div className="lg:col-span-2 glass-card rounded-2xl p-6">
          {/* Calendar Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              <button
                onClick={goToPreviousMonth}
                className="p-2 glass-card rounded-xl text-zinc-400 hover:text-white transition-colors"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              <h2 className="text-xl font-semibold text-white min-w-[200px] text-center">
                {MONTHS[currentDate.getMonth()]} {currentDate.getFullYear()}
              </h2>
              <button
                onClick={goToNextMonth}
                className="p-2 glass-card rounded-xl text-zinc-400 hover:text-white transition-colors"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
            <button
              onClick={goToToday}
              className="px-4 py-2 text-sm text-zinc-400 hover:text-white glass-card rounded-xl transition-colors"
            >
              Today
            </button>
          </div>

          {/* Days Header */}
          <div className="grid grid-cols-7 gap-0 mb-2">
            {DAYS.map((day) => (
              <div
                key={day}
                className="text-center text-sm font-medium text-zinc-500 py-2"
              >
                {day}
              </div>
            ))}
          </div>

          {/* Calendar Grid */}
          <div className="grid grid-cols-7 gap-0 rounded-xl overflow-hidden border border-zinc-800">
            {calendarDays.map((day, index) => (
              <CalendarDay
                key={index}
                date={day.date}
                isCurrentMonth={day.isCurrentMonth}
                isToday={
                  day.date.getDate() === today.getDate() &&
                  day.date.getMonth() === today.getMonth() &&
                  day.date.getFullYear() === today.getFullYear()
                }
                events={filteredEvents}
                onSelectDate={setSelectedDate}
                isSelected={
                  selectedDate !== null &&
                  day.date.getDate() === selectedDate.getDate() &&
                  day.date.getMonth() === selectedDate.getMonth() &&
                  day.date.getFullYear() === selectedDate.getFullYear()
                }
              />
            ))}
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Selected Date Events */}
          {selectedDate && (
            <div className="glass-card rounded-2xl p-6">
              <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
                <CalendarIcon className="w-5 h-5 text-purple-400" />
                {selectedDate.getDate()} {MONTHS[selectedDate.getMonth()]}
              </h3>
              {selectedDateEvents.length > 0 ? (
                <div className="space-y-3">
                  {selectedDateEvents.map((event) => (
                    <EventCard key={event.id} event={event} />
                  ))}
                </div>
              ) : (
                <p className="text-sm text-zinc-500 text-center py-4">
                  Aucun événement pour cette date
                </p>
              )}
            </div>
          )}

          {/* Upcoming Events */}
          <div className="glass-card rounded-2xl p-6">
            <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
              <Clock className="w-5 h-5 text-purple-400" />
              Prochains événements
            </h3>
            {upcomingEvents.length > 0 ? (
              <div className="space-y-3">
                {upcomingEvents.slice(0, 5).map((event) => (
                  <div key={event.id} className="flex items-center gap-3 p-3 rounded-xl bg-zinc-800/30">
                    <div className={`w-2 h-2 rounded-full ${eventTypeConfig[event.type].color}`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-zinc-200 truncate">{event.title}</p>
                      <p className="text-xs text-zinc-500">
                        {event.date.getDate()} {MONTHS[event.date.getMonth()].slice(0, 3)}
                        {event.time && ` · ${event.time}`}
                      </p>
                    </div>
                    {event.agent_name && (
                      <span className="text-xs text-zinc-500 flex items-center gap-1">
                        <Bot className="w-3 h-3" />
                        {event.agent_name}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-zinc-500 text-center py-4">
                Aucun événement prévu
              </p>
            )}
          </div>

          {/* Quick Actions */}
          <div className="glass-card rounded-2xl p-6">
            <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
              <Play className="w-5 h-5 text-purple-400" />
              Actions rapides
            </h3>
            <div className="space-y-2">
              <button className="w-full flex items-center gap-3 p-3 rounded-xl bg-zinc-800/30 hover:bg-zinc-700/50 transition-colors text-left">
                <RefreshCw className="w-4 h-4 text-purple-400" />
                <span className="text-sm text-zinc-300">Trigger Daily Report</span>
              </button>
              <button className="w-full flex items-center gap-3 p-3 rounded-xl bg-zinc-800/30 hover:bg-zinc-700/50 transition-colors text-left">
                <Target className="w-4 h-4 text-amber-400" />
                <span className="text-sm text-zinc-300">View All Goals</span>
              </button>
              <button className="w-full flex items-center gap-3 p-3 rounded-xl bg-zinc-800/30 hover:bg-zinc-700/50 transition-colors text-left">
                <Clock className="w-4 h-4 text-cyan-400" />
                <span className="text-sm text-zinc-300">Scheduled Actions</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Calendar;
