import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { MessageSquare, X, Send, User, Bot, AlertTriangle, Play } from 'lucide-react';

export default function ChatWidget({ onActionCompleted, selectedCustomer }) {
  const [isOpen, setIsOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [history, setHistory] = useState([
    {
      sender: 'bot',
      text: "Hello! I am the FinSense Multi-Agent assistant. How can I assist you today? Try clicking one of the testing flows below!",
      agent: 'Router'
    }
  ]);
  const [loading, setLoading] = useState(false);
  
  // Custom states to simulate session context
  const [context, setContext] = useState({
    customer_id: 'CUST001',
    pan: 'ABCDE1234F',
    aadhaar: '123456789012'
  });

  useEffect(() => {
    if (selectedCustomer) {
      setContext({
        customer_id: selectedCustomer.customer_id,
        pan: selectedCustomer.pan,
        aadhaar: selectedCustomer.aadhaar
      });
      setHistory(prev => [
        ...prev,
        {
          sender: 'bot',
          text: `Context switched to customer ${selectedCustomer.name} (${selectedCustomer.customer_id}).`,
          agent: 'Router'
        }
      ]);
    }
  }, [selectedCustomer]);

  const quickTests = [
    { label: "1. Check CKYC (Priya Patel)", text: "Verify CKYC status for Priya Patel", pan: "FGHIJ5678K" },
    { label: "2. Approve KYC (CUST002)", text: "Approve KYC check", customer_id: "CUST002" },
    { label: "3. Open Account (CUST002)", text: "Open savings account with Rs. 15000", customer_id: "CUST002", deposit: 15000 },
    { label: "4. Check Balance (CUST001)", text: "Check account balance", customer_id: "CUST001" },
    { label: "5. UPI Rs.500 (Aarav -> Rohan)", text: "Send Rs. 500 UPI payment", sender_upi: "aarav@oksbi", receiver_upi: "rohan@oksbi", amount: 500, remarks: "Dinner split" },
    { label: "6. Check Risk Flag (CUST003)", text: "Check suspicious activity flag", customer_id: "CUST003" },
    { label: "7. Recommend Card (CUST001)", text: "What credit card am I eligible for?", customer_id: "CUST001" }
  ];

  const handleSendMessage = async (textToSend, customContext = null) => {
    const text = textToSend || message;
    if (!text.trim()) return;

    // Add user message
    const newMsg = { sender: 'user', text };
    setHistory(prev => [...prev, newMsg]);
    setMessage('');
    setLoading(true);

    const activeContext = customContext || context;

    try {
      const res = await axios.post('/api/chat', {
        message: text,
        customer_id: activeContext.customer_id,
        context: activeContext
      });

      setHistory(prev => [
        ...prev,
        {
          sender: 'bot',
          text: res.data.response,
          agent: res.data.agent,
          status: res.data.status,
          risk: res.data.risk_indicator
        }
      ]);

      // Trigger dashboard reload on completions
      if (res.data.status === 'COMPLETED' || res.data.status === 'FLAGGED') {
        if (onActionCompleted) onActionCompleted();
      }
    } catch (err) {
      console.error(err);
      setHistory(prev => [
        ...prev,
        {
          sender: 'bot',
          text: "Sorry, I encountered an error connecting to the FinSense Agent Router.",
          agent: "System Error"
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const runQuickTest = (test) => {
    const testContext = {
      customer_id: test.customer_id || context.customer_id,
      pan: test.pan || context.pan,
      aadhaar: test.aadhaar || context.aadhaar,
      deposit: test.deposit,
      sender_upi: test.sender_upi,
      receiver_upi: test.receiver_upi,
      amount: test.amount,
      remarks: test.remarks
    };
    handleSendMessage(test.text, testContext);
  };

  return (
    <>
      {/* Floating Action Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 bg-blue-600 hover:bg-blue-700 text-white rounded-full p-4 shadow-lg hover:scale-105 transition-all z-50 flex items-center gap-2"
        >
          <MessageSquare className="w-6 h-6" />
          <span className="font-semibold text-sm pr-1">Agent Console</span>
        </button>
      )}

      {/* Chat Window Panel */}
      {isOpen && (
        <div className="fixed bottom-6 right-6 w-96 h-[550px] bg-zinc-900 border border-zinc-800 rounded-2xl shadow-2xl flex flex-col z-50 overflow-hidden font-sans">
          
          {/* Header */}
          <div className="bg-zinc-950 p-4 border-b border-zinc-800 flex justify-between items-center">
            <div className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping"></div>
              <div>
                <h3 className="font-bold text-sm text-zinc-50">FinSense Agent Router</h3>
                <p className="text-xs text-zinc-400">Active Multi-Agent Session</p>
              </div>
            </div>
            <button onClick={() => setIsOpen(false)} className="text-zinc-400 hover:text-zinc-50 transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Main Body */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-zinc-950/40">
            {history.map((msg, index) => (
              <div key={index} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] rounded-xl p-3 text-sm ${msg.sender === 'user' ? 'bg-blue-600 text-white rounded-br-none' : 'bg-zinc-800 text-zinc-200 border border-zinc-700 rounded-bl-none'}`}>
                  
                  {/* Agent badge */}
                  {msg.sender === 'bot' && (
                    <div className="flex items-center gap-1.5 text-[10px] font-semibold tracking-wider text-blue-400 uppercase mb-1">
                      <Bot className="w-3 h-3" />
                      {msg.agent}
                    </div>
                  )}

                  <div className="whitespace-pre-line leading-relaxed font-sans">{msg.text}</div>
                  
                  {/* Risk Alert Flag */}
                  {msg.risk && (
                    <div className="mt-2 flex items-center gap-1.5 bg-rose-950/40 border border-rose-800/40 text-rose-400 rounded-md p-1.5 text-xs">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      Flagged: {msg.risk}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-zinc-800 text-zinc-400 rounded-xl rounded-bl-none p-3 text-sm border border-zinc-700 flex items-center gap-2">
                  <div className="w-2 h-2 bg-zinc-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                  <div className="w-2 h-2 bg-zinc-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                  <div className="w-2 h-2 bg-zinc-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                </div>
              </div>
            )}
          </div>

          {/* Quick Test Swatches */}
          <div className="px-4 py-2 border-t border-zinc-800 bg-zinc-900">
            <p className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider mb-1">Quick Sandbox Scenarios</p>
            <div className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-thin scrollbar-thumb-zinc-700">
              {quickTests.map((t, idx) => (
                <button
                  key={idx}
                  onClick={() => runQuickTest(t)}
                  className="flex-shrink-0 flex items-center gap-1 bg-zinc-850 hover:bg-zinc-800 border border-zinc-700 text-[11px] text-zinc-300 rounded px-2.5 py-1 transition-all hover:border-blue-500/50"
                >
                  <Play className="w-2.5 h-2.5 text-emerald-500 fill-emerald-500" />
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Input Footer */}
          <div className="p-3 border-t border-zinc-800 bg-zinc-950 flex gap-2">
            <input
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
              placeholder="Ask onboarding, adopt, engage agents..."
              className="flex-1 bg-zinc-900 border border-zinc-850 text-zinc-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-zinc-700 focus:ring-1 focus:ring-zinc-700"
            />
            <button
              onClick={() => handleSendMessage()}
              className="bg-blue-600 hover:bg-blue-700 text-white rounded-lg p-2 transition-colors"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
