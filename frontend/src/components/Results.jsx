import React from 'react';
import { motion } from 'framer-motion';
import './Results.css';

const Results = ({ results, onVote }) => {
    const agents = [
        { id: 'lime', title: 'LIME Evidence', data: results.lime },
        { id: 'standard', title: 'Standard Suggestion', data: results.standard },
        { id: 'cot', title: 'Chain of Thought', data: results.cot },
        { id: 'self_check', title: 'Self-Check', data: results.self_check },
    ];

    return (
        <div className="results-container">
            <h2>Budget Proposals</h2>
            <div className="cards-grid">
                {agents.map((agent, index) => (
                    <motion.div
                        key={agent.id}
                        className="result-card"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.2 }}
                    >
                        <div className="card-header">
                            <h3>{agent.title}</h3>
                        </div>

                        <div className="card-body">
                            {agent.data.error ? (
                                <p className="error">{agent.data.error}</p>
                            ) : (
                                <>
                                    <div className="budget-list">
                                        <h4>Proposed Budget:</h4>
                                        <ul>
                                            {Object.entries(agent.data.advice || {}).map(([cat, amount]) => (
                                                <li key={cat}>
                                                    <span>{cat}</span>
                                                    <span>${amount}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>

                                    <div className="explanation-section">
                                        <h4>Explanation:</h4>
                                        <p>{agent.data.explanation}</p>
                                    </div>

                                    {agent.data.savings_advice && (
                                        <div className="savings-section">
                                            <h4>Savings Advice:</h4>
                                            <p>{agent.data.savings_advice}</p>
                                        </div>
                                    )}
                                </>
                            )}
                        </div>

                        <div className="card-footer">
                            <button onClick={() => onVote(agent.id)}>
                                Vote for this Plan
                            </button>
                        </div>
                    </motion.div>
                ))}
            </div>
        </div>
    );
};

export default Results;
