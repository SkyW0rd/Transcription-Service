import { PipelineStage } from '../types';

interface PipelineViewProps {
  stages: PipelineStage[];
}

export function PipelineView({ stages }: PipelineViewProps) {
  return (
    <div className="pipeline" aria-label="Этапы обработки">
      {stages.map((stage, index) => (
        <div key={stage.key} className="pipeline-stage-wrap">
          <div className={`pipeline-stage pipeline-${stage.status}`}>
            <span className="pipeline-indicator" />
            <span>{stage.label}</span>
          </div>
          {index < stages.length - 1 && <div className="pipeline-connector" />}
        </div>
      ))}
    </div>
  );
}
