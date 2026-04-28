import { DashboardStatsData } from '../types';

interface DashboardStatsProps {
  stats: DashboardStatsData;
}

export function DashboardStats({ stats }: DashboardStatsProps) {
  const cards = [
    { label: 'Всего задач', value: stats.total },
    { label: 'В работе', value: stats.processing },
    { label: 'Готово', value: stats.completed },
    { label: 'Сбои / отмена', value: stats.failed },
  ];

  return (
    <section className="stats-grid" aria-label="Статистика">
      {cards.map((card) => (
        <article key={card.label} className="stat-card">
          <span className="stat-label">{card.label}</span>
          <strong className="stat-value">{card.value}</strong>
        </article>
      ))}
    </section>
  );
}
