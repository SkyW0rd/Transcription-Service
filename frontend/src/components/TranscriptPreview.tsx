import { SpeakerSegment } from '../types';

interface TranscriptPreviewProps {
  transcript?: string | null;
  speakerSegments?: SpeakerSegment[];
  loading?: boolean;
}

export function TranscriptPreview({ transcript, speakerSegments, loading }: TranscriptPreviewProps) {
  if (loading) {
    return (
      <section className="detail-block">
        <h4>Текст (Speech-to-Text)</h4>
        <div className="skeleton-block" />
      </section>
    );
  }

  if (!transcript && (!speakerSegments || speakerSegments.length === 0)) {
    return (
      <section className="detail-block">
        <h4>Текст (Speech-to-Text)</h4>
        <div className="empty-state small">Текст появится после этапа транскрибации.</div>
      </section>
    );
  }

  return (
    <section className="detail-block">
      <h4>Текст (Speech-to-Text)</h4>
      <div className="transcript-box">
        {speakerSegments && speakerSegments.length > 0 ? (
          speakerSegments.map((segment, index) => (
            <article key={`${segment.start}-${index}`} className="segment-row">
              <div className="segment-header">
                <strong>{segment.speaker}</strong>
                <span>
                  {segment.start}–{segment.end}
                </span>
              </div>
              <p>{segment.text}</p>
            </article>
          ))
        ) : (
          <p className="preserve-lines">{transcript}</p>
        )}
      </div>
    </section>
  );
}
