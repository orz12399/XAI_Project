import React from 'react';
import './Scoreboard.css';

const Scoreboard = ({ scores }) => {
    return (
        <div className="scoreboard">
            <h3>AI Trust Scoreboard</h3>
            <div className="scores-grid">
                <div className="score-item">
                    <span className="agent-name">LIME (Evidence)</span>
                    <span className="score-value">{scores.lime}</span>
                </div>
                <div className="score-item">
                    <span className="agent-name">Standard</span>
                    <span className="score-value">{scores.standard}</span>
                </div>
                <div className="score-item">
                    <span className="agent-name">CoT (Reasoning)</span>
                    <span className="score-value">{scores.cot}</span>
                </div>
                <div className="score-item">
                    <span className="agent-name">Self-Check</span>
                    <span className="score-value">{scores.self_check}</span>
                </div>
            </div>
        </div>
    );
};

export default Scoreboard;
