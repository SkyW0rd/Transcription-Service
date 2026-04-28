interface DownloadSummaryButtonProps {
  url: string | null;
  disabled?: boolean;
}

export function DownloadSummaryButton({ url, disabled }: DownloadSummaryButtonProps) {
  if (!url || disabled) {
    return (
      <button type="button" className="secondary-button" disabled>
        PDF ещё не готов
      </button>
    );
  }

  return (
    <a className="primary-button" href={url} download>
      Скачать PDF
    </a>
  );
}
