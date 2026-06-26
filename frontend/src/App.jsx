import React, { useState } from 'react';
import BankerDashboard from './components/BankerDashboard';
import ChatWidget from './components/ChatWidget';

export default function App() {
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleCustomerSelect = (customer) => {
    setSelectedCustomer(customer);
  };

  const handleActionCompleted = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-50 flex flex-col font-sans selection:bg-zinc-800 selection:text-white">
      {/* Top subtle ambient glow */}
      <div className="absolute top-0 left-0 right-0 h-[300px] bg-gradient-to-b from-blue-900/10 to-transparent pointer-events-none z-0"></div>
      
      {/* Main dashboard view */}
      <main className="flex-1 z-10">
        <BankerDashboard 
          refreshTrigger={refreshTrigger}
          onCustomerSelect={handleCustomerSelect} 
        />
      </main>

      {/* Floating conversational Agent Widget */}
      <ChatWidget 
        selectedCustomer={selectedCustomer}
        onActionCompleted={handleActionCompleted}
      />
    </div>
  );
}
