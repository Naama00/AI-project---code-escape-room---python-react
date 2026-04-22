import { useState, useEffect } from 'react';
import './index.css';

function App() {
  // State variables for the game
  const [currentTask, setCurrentTask] = useState(null);
  // Randomize initial task ID between 1-10
  const [taskId, setTaskId] = useState(() => Math.floor(Math.random() * 10) + 1);
  const [code, setCode] = useState('');
  const [feedbackHistory, setFeedbackHistory] = useState([]); // Stores AI feedback
  const [isLoading, setIsLoading] = useState(false); // UI state for loading
  const [autoAdvanceTimer, setAutoAdvanceTimer] = useState(null); // Timer for auto-next task

  // Fetch task data from the backend when taskId changes
  useEffect(() => {
    const fetchTask = async () => {
      try {
const response = await fetch(`http://localhost:5000/get-task/${taskId}`);
        const data = await response.json();
        setCurrentTask(data);
        setCode(data.bad_code); // Populate editor with bad code
      } catch (error) {
        console.error('Error fetching task:', error);
      }
    };

    fetchTask();
  }, [taskId]);

  // Handle manual navigation to the next task
  const handleNextTask = () => {
    if (autoAdvanceTimer) {
      clearTimeout(autoAdvanceTimer);
      setAutoAdvanceTimer(null);
    }
    setTaskId(prev => prev + 1);
  };

  // Submit code to backend for AI analysis
  const submitCode = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:5000/analyze-code', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          code: code,
          task_id: taskId
        }),
      });

      if (!response.ok) {
        throw new Error(`Server Error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      
      // Create a feedback object and add it to history
      const newFeedback = {
        ...data.feedback,
        taskId: taskId,
        taskTitle: currentTask.title,
        timestamp: new Date().toLocaleTimeString('en-US')
      };
      setFeedbackHistory(prev => [newFeedback, ...prev]);

      // If code is solved, set a timer to automatically advance to the next task
      if (data.feedback.is_solved) {
        const timer = setTimeout(() => {
          setTaskId(prev => prev + 1);
        }, 10000); // 10 seconds delay
        setAutoAdvanceTimer(timer);
      }
      
    } catch (error) {
      console.error('Error submitting code:', error);
      alert(`Error: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Loading state UI
  if (!currentTask) return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="text-center">
        <p className="text-3xl font-bold text-sky-600 mb-3 float">Loading Level...</p>
        <div className="text-6xl float" style={{animationDelay: '0.2s'}}>🎮</div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 pb-12">
      
      {/* Header Section */}
      <header className="bg-white shadow-sm sticky top-0 z-50 border-b border-slate-100">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className='flex items-center gap-3'>
            <div className='text-4xl'>👨‍💻</div>
            <h1 className="text-3xl font-black text-slate-950">
              Code <span className='text-sky-500'>Escape</span> Room
            </h1>
          </div>
          <div className="flex items-center gap-2 bg-sky-50 text-sky-700 px-4 py-2 rounded-full font-bold">
            <span>Level:</span>
            <span className='text-xl'>{taskId}</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        
        {/* Game Instructions */}
        <div className="bg-white p-6 rounded-3xl shadow-sm border border-sky-100 mb-8 flex gap-4 items-center">
            <div className='text-4xl'>💡</div>
            <div>
                <h2 className='text-lg font-bold text-slate-900'>How to Play?</h2>
                <p className='text-slate-600'>Read the challenge, refactor the code in the editor below, and click "Check Code" to get AI feedback. Goal: Clean, efficient, and readable code!</p>
            </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          
          {/* Task Panel (Where user reads and types) */}
          <div className="bg-white p-6 rounded-3xl shadow-lg border border-slate-100">
            <div className="text-xl font-bold text-slate-800 mb-4 flex items-center gap-2">
              <span>📋</span> Challenge: {currentTask.title}
            </div>
            <p className="text-slate-700 mb-4 bg-slate-100 p-4 rounded-xl">{currentTask.description}</p>
            
            <div className="text-xl font-bold text-slate-800 mb-4 flex items-center gap-2 mt-6">
              <span>🛠️</span> Edit your code here:
            </div>
            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className="w-full h-96 p-4 font-mono text-sm rounded-2xl border-2 border-sky-100 bg-slate-950 text-sky-300 focus:border-sky-300 focus:ring-2 focus:ring-sky-200 resize-none outline-none transition"
              spellCheck="false"
            />
            
            <button
              onClick={submitCode}
              disabled={isLoading}
              className={`mt-6 w-full px-6 py-3 rounded-full font-bold text-white transition-all duration-200 transform hover:scale-105 active:scale-95 ${isLoading ? 'bg-slate-400' : 'bg-gradient-to-r from-cyan-400 to-blue-500'}`}
            >
              {isLoading ? '🤖 Analyzing...' : '🚀 Check Code'}
            </button>
          </div>

          {/* Feedback Panel (AI Responses) */}
          <div className="bg-white p-6 rounded-3xl shadow-lg border border-slate-100">
            <div className="text-xl font-bold text-slate-800 mb-4 flex items-center gap-2">
              <span>🤖</span> AI Feedback
            </div>
            
            {feedbackHistory.length === 0 ? (
                <div className='text-center py-12 text-slate-500'>
                    <div className='text-5xl mb-4'>🧐</div>
                    Submit code to receive analysis and hints.
                </div>
            ) : (
                <div className="space-y-4 max-h-[600px] overflow-y-auto pr-2">
                  {feedbackHistory.map((fb, index) => (
                    <div key={index} className={`p-4 rounded-xl border ${fb.is_solved ? 'bg-green-50 border-green-200' : 'bg-slate-50 border-slate-200'}`}>
                      <div className='flex justify-between text-sm mb-2'>
                        <span className='font-bold'>{fb.taskTitle}</span>
                        <span className='text-slate-500'>{fb.timestamp}</span>
                      </div>
                      <p className="text-sm text-slate-700">{fb.commentary}</p>
                      {fb.score && <p className='font-bold mt-2 text-sky-700'>Score: {fb.score}/100</p>}
                    </div>
                  ))}
                </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
