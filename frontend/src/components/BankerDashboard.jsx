import React, { useState, useEffect } from 'react';
import axios from 'axios';
import ReactECharts from 'echarts-for-react';
import { Users, CreditCard, AlertOctagon, TrendingUp, CheckCircle, Clock, XCircle, Search, RefreshCw, Layers } from 'lucide-react';

export default function BankerDashboard({ onCustomerSelect, refreshTrigger }) {
  const [customers, setCustomers] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [selectedCust, setSelectedCust] = useState(null);
  const [custTxns, setCustTxns] = useState([]);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(false);
  const [filterQuery, setFilterQuery] = useState('');

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const [custRes, txRes, graphRes] = await Promise.all([
        axios.get('/api/customers'),
        axios.get('/api/transactions'),
        axios.get('/api/graph')
      ]);
      setCustomers(custRes.data);
      setTransactions(txRes.data);
      setGraphData(graphRes.data);

      if (selectedCust) {
        // Refresh selected customer details
        const updated = custRes.data.find(c => c.customer_id === selectedCust.customer_id);
        if (updated) setSelectedCust(updated);
      }
    } catch (err) {
      console.error("Error fetching banker dashboard data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [refreshTrigger]);

  useEffect(() => {
    if (selectedCust) {
      // Filter transactions for this customer
      const filtered = transactions.filter(t => t.customer_id === selectedCust.customer_id);
      setCustTxns(filtered);
    } else {
      setCustTxns([]);
    }
  }, [selectedCust, transactions]);

  // Compute metrics
  const totalBalance = customers.reduce((sum, c) => {
    const accBal = c.accounts?.reduce((s, a) => s + a.balance, 0) || 0;
    return sum + accBal;
  }, 0);

  const flaggedTxnsCount = transactions.filter(t => t.description.toLowerCase().includes('crypto') || t.status === 'FAILED').length;

  const filteredCustomers = customers.filter(c => 
    c.name.toLowerCase().includes(filterQuery.toLowerCase()) ||
    c.customer_id.toLowerCase().includes(filterQuery.toLowerCase()) ||
    c.pan.toLowerCase().includes(filterQuery.toLowerCase())
  );

  // ECharts Graph Configuration
  const graphOption = React.useMemo(() => {
    if (!graphData.nodes || graphData.nodes.length === 0) return {};

    // Filter nodes/links if a customer is selected to focus the view, or display full registry graph
    let nodesToRender = graphData.nodes;
    let linksToRender = graphData.links;

    if (selectedCust) {
      const relatedNodeIds = new Set([selectedCust.customer_id]);
      
      // Add immediately connected nodes (accounts, risk profiles, product interests)
      graphData.links.forEach(link => {
        const src = typeof link.source === 'object' ? link.source.id : link.source;
        const tgt = typeof link.target === 'object' ? link.target.id : link.target;
        
        if (src === selectedCust.customer_id) {
          relatedNodeIds.add(tgt);
        }
        if (tgt === selectedCust.customer_id) {
          relatedNodeIds.add(src);
        }
      });

      // Include edges between related nodes
      nodesToRender = graphData.nodes.filter(n => relatedNodeIds.has(n.id));
      linksToRender = graphData.links.filter(l => {
        const src = typeof l.source === 'object' ? l.source.id : l.source;
        const tgt = typeof l.target === 'object' ? l.target.id : l.target;
        return relatedNodeIds.has(src) && relatedNodeIds.has(tgt);
      });
    }

    const categories = [
      { name: 'Customer' },
      { name: 'Account' },
      { name: 'Risk' },
      { name: 'Product' }
    ];

    const chartNodes = nodesToRender.map(node => {
      let size = 30;
      let color = '#3b82f6'; // Blue for customers
      let categoryIdx = 0;

      if (node.type === 'Account') {
        size = 25;
        color = '#10b981'; // Green for accounts
        categoryIdx = 1;
      } else if (node.type === 'RiskCategory' || node.type === 'RiskIndicator') {
        size = 22;
        color = '#f59e0b'; // Amber for risks
        categoryIdx = 2;
        if (node.id && typeof node.id === 'string' && (node.id.includes('High') || node.id.includes('Crypto'))) {
          color = '#ef4444'; // Red for severe risk
        }
      } else if (node.type === 'Product') {
        size = 20;
        color = '#8b5cf6'; // Purple for products
        categoryIdx = 3;
      }

      return {
        id: node.id,
        name: node.label || node.id,
        symbolSize: size,
        value: node.type,
        category: categoryIdx,
        itemStyle: { color: color },
        label: {
          show: true,
          position: 'right',
          color: '#e4e4e7',
          fontSize: 10,
          fontFamily: 'DM Sans, sans-serif'
        }
      };
    });

    const chartLinks = linksToRender.map(link => {
      const src = typeof link.source === 'object' ? link.source.id : link.source;
      const tgt = typeof link.target === 'object' ? link.target.id : link.target;
      return {
        source: src,
        target: tgt,
        label: {
          show: true,
          formatter: link.relation || '',
          fontSize: 8,
          color: '#71717a'
        },
        lineStyle: {
          color: '#27272a',
          width: 1.5,
          curveness: 0.1
        }
      };
    });

    return {
      title: {
        text: selectedCust ? `${selectedCust.name} Relations Graph` : 'SBI Central intelligence Memory Graph',
        textStyle: {
          color: '#fafafa',
          fontSize: 14,
          fontFamily: 'DM Sans, sans-serif'
        },
        left: '5%',
        top: '5%'
      },
      tooltip: {
        backgroundColor: '#09090b',
        borderColor: '#27272a',
        textStyle: { color: '#fafafa' }
      },
      legend: [
        {
          data: categories.map(c => c.name),
          textStyle: { color: '#a1a1aa', fontSize: 10 },
          bottom: '5%'
        }
      ],
      series: [
        {
          type: 'graph',
          layout: 'force',
          data: chartNodes,
          links: chartLinks,
          categories: categories,
          roam: true,
          label: {
            position: 'right'
          },
          force: {
            repulsion: 120,
            edgeLength: 100
          },
          lineStyle: {
            color: 'source',
            curveness: 0.3
          }
        }
      ]
    };
  }, [graphData, selectedCust]);

  const handleRowClick = (cust) => {
    setSelectedCust(cust);
    if (onCustomerSelect) onCustomerSelect(cust);
  };

  return (
    <div className="flex flex-col gap-6 max-w-[1600px] mx-auto p-6 font-sans">
      
      {/* Top Banner Row */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-zinc-50">FinSense AI Console</h1>
          <p className="text-sm text-zinc-400">SBI Digital Banking Onboarding, Adoption & Security Portal</p>
        </div>
        <button
          onClick={fetchDashboardData}
          disabled={loading}
          className="flex items-center gap-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 rounded-lg px-4 py-2 font-medium text-sm transition-all shadow-sm disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh Console
        </button>
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
        
        {/* Total Customers */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Total Registry Customers</p>
            <h3 className="text-3xl font-bold font-mono text-zinc-50 mt-1">{customers.length}</h3>
            <span className="inline-flex items-center gap-1 text-[11px] bg-emerald-950/40 text-emerald-400 rounded-full px-2 py-0.5 mt-2.5 font-medium">
              <TrendingUp className="w-3 h-3" />
              +15% monthly
            </span>
          </div>
          <div className="bg-blue-600/10 text-blue-500 rounded-xl p-3 border border-blue-500/20">
            <Users className="w-6 h-6" />
          </div>
        </div>

        {/* Assets Under Management */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Mock Savings Deposits</p>
            <h3 className="text-3xl font-bold font-mono text-zinc-50 mt-1">₹{totalBalance.toLocaleString('en-IN')}</h3>
            <span className="inline-flex items-center gap-1 text-[11px] bg-emerald-950/40 text-emerald-400 rounded-full px-2 py-0.5 mt-2.5 font-medium">
              <TrendingUp className="w-3 h-3" />
              +2.3% weekly
            </span>
          </div>
          <div className="bg-emerald-600/10 text-emerald-500 rounded-xl p-3 border border-emerald-500/20">
            <CreditCard className="w-6 h-6" />
          </div>
        </div>

        {/* Risk Alerts */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Security Flagged Activities</p>
            <h3 className="text-3xl font-bold font-mono text-zinc-50 mt-1">{flaggedTxnsCount}</h3>
            <span className={`inline-flex items-center gap-1 text-[11px] rounded-full px-2 py-0.5 mt-2.5 font-medium ${flaggedTxnsCount > 0 ? 'bg-rose-950/40 text-rose-400' : 'bg-zinc-800 text-zinc-400'}`}>
              <AlertOctagon className="w-3 h-3" />
              {flaggedTxnsCount > 0 ? 'Needs attention' : 'All secure'}
            </span>
          </div>
          <div className={`rounded-xl p-3 border ${flaggedTxnsCount > 0 ? 'bg-rose-600/10 text-rose-500 border-rose-500/20' : 'bg-zinc-800/40 text-zinc-400 border-zinc-700/20'}`}>
            <AlertOctagon className="w-6 h-6" />
          </div>
        </div>

        {/* Active Agents */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Multi-Agent Roster</p>
            <h3 className="text-3xl font-bold font-mono text-zinc-50 mt-1">3 Active</h3>
            <span className="inline-flex items-center gap-1 text-[11px] bg-blue-950/40 text-blue-400 rounded-full px-2 py-0.5 mt-2.5 font-medium">
              <Layers className="w-3 h-3" />
              Router Enabled
            </span>
          </div>
          <div className="bg-purple-600/10 text-purple-500 rounded-xl p-3 border border-purple-500/20">
            <Layers className="w-6 h-6" />
          </div>
        </div>

      </div>

      {/* Main Content split */}
      <div className="flex flex-col lg:flex-row gap-6">
        
        {/* Left Column: Customer Registry */}
        <div className={`bg-zinc-900 border border-zinc-800 rounded-xl p-5 shadow-sm transition-all duration-300 ${selectedCust ? 'w-full lg:w-3/5' : 'w-full'}`}>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-bold text-zinc-50">Central Customer Registry</h2>
            
            {/* Search Input */}
            <div className="relative w-64">
              <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search name, customer ID, PAN..."
                value={filterQuery}
                onChange={(e) => setFilterQuery(e.target.value)}
                className="w-full bg-zinc-950 border border-zinc-800 text-zinc-100 rounded-md pl-9 pr-3 py-1.5 text-xs focus:outline-none focus:border-zinc-700"
              />
            </div>
          </div>

          <div className="overflow-x-auto rounded-lg border border-zinc-800">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-zinc-950 text-zinc-400 text-xs font-semibold tracking-wider border-b border-zinc-800">
                  <th className="p-3">Customer ID</th>
                  <th className="p-3">Name</th>
                  <th className="p-3">PAN</th>
                  <th className="p-3">KYC Status</th>
                  <th className="p-3">Risk Assessment</th>
                  <th className="p-3">Accounts Linked</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800 text-xs text-zinc-300">
                {filteredCustomers.map(cust => (
                  <tr
                    key={cust.customer_id}
                    onClick={() => handleRowClick(cust)}
                    className={`cursor-pointer transition-colors duration-200 ${selectedCust?.customer_id === cust.customer_id ? 'bg-blue-900/20 hover:bg-blue-900/30' : 'hover:bg-zinc-850'}`}
                  >
                    <td className="p-3 font-mono text-zinc-400">{cust.customer_id}</td>
                    <td className="p-3 font-semibold text-zinc-100">{cust.name}</td>
                    <td className="p-3 font-mono">{cust.pan}</td>
                    <td className="p-3">
                      <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${
                        cust.kyc_status === 'COMPLETED' ? 'bg-emerald-950/50 text-emerald-400 border border-emerald-800/20' : 
                        cust.kyc_status === 'PENDING' ? 'bg-amber-950/50 text-amber-400 border border-amber-800/20' : 
                        'bg-zinc-800 text-zinc-400'
                      }`}>
                        {cust.kyc_status === 'COMPLETED' ? <CheckCircle className="w-2.5 h-2.5" /> : <Clock className="w-2.5 h-2.5" />}
                        {cust.kyc_status}
                      </span>
                    </td>
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        {/* Risk Sparkline Progress Bar */}
                        <div className="w-20 bg-zinc-800 rounded-full h-1.5 overflow-hidden">
                          <div 
                            className={`h-full ${cust.risk_score > 70 ? 'bg-rose-500' : cust.risk_score > 30 ? 'bg-amber-400' : 'bg-emerald-500'}`} 
                            style={{ width: `${cust.risk_score}%` }}
                          ></div>
                        </div>
                        <span className="font-semibold font-mono">{cust.risk_score}%</span>
                      </div>
                    </td>
                    <td className="p-3 font-semibold text-zinc-400">{cust.accounts?.length || 0} A/Cs</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {filteredCustomers.length === 0 && (
            <div className="text-center py-8 text-zinc-500 text-sm">No customers matching search criteria.</div>
          )}
        </div>

        {/* Right Column: Details Panel & Graph Visualization */}
        {selectedCust && (
          <div className="w-full lg:w-2/5 bg-zinc-900 border border-zinc-800 rounded-xl p-5 shadow-sm flex flex-col gap-5 relative animate-fade-in">
            <button
              onClick={() => setSelectedCust(null)}
              className="absolute top-4 right-4 text-zinc-400 hover:text-zinc-100 transition-colors"
            >
              Close
            </button>

            {/* Profile Overview */}
            <div>
              <span className="text-[10px] font-bold text-blue-400 tracking-wider uppercase">Active Customer Details</span>
              <h2 className="text-xl font-bold text-zinc-50 mt-1">{selectedCust.name}</h2>
              <div className="grid grid-cols-2 gap-4 mt-3 bg-zinc-950/40 border border-zinc-800/40 rounded-lg p-3 text-xs">
                <div>
                  <p className="text-zinc-500 font-semibold uppercase tracking-wider text-[10px]">Aadhaar Number</p>
                  <p className="font-mono text-zinc-300 mt-0.5">{selectedCust.aadhaar || 'Not Verified'}</p>
                </div>
                <div>
                  <p className="text-zinc-500 font-semibold uppercase tracking-wider text-[10px]">Phone Number</p>
                  <p className="font-mono text-zinc-300 mt-0.5">{selectedCust.phone}</p>
                </div>
                <div className="col-span-2">
                  <p className="text-zinc-500 font-semibold uppercase tracking-wider text-[10px]">Email Address</p>
                  <p className="font-mono text-zinc-300 mt-0.5">{selectedCust.email}</p>
                </div>
              </div>
            </div>

            {/* ECharts Network Memory Graph */}
            <div className="bg-zinc-950 border border-zinc-800 rounded-xl h-64 overflow-hidden relative">
              <ReactECharts 
                option={graphOption} 
                style={{ height: '100%', width: '100%' }}
                notMerge={true}
              />
            </div>

            {/* Customer Accounts and Balances */}
            <div>
              <h3 className="text-sm font-bold text-zinc-50 mb-2">Linked Bank Accounts</h3>
              {selectedCust.accounts && selectedCust.accounts.length > 0 ? (
                selectedCust.accounts.map(acc => (
                  <div key={acc.account_number} className="bg-zinc-950/60 border border-zinc-800 rounded-lg p-3 flex justify-between items-center text-xs">
                    <div>
                      <p className="font-semibold text-zinc-200">SBI Savings Account</p>
                      <p className="font-mono text-zinc-500 mt-0.5">{acc.account_number}</p>
                      <p className="font-mono text-blue-400 mt-1 bg-zinc-900 border border-zinc-800 rounded px-1.5 py-0.5 inline-block text-[10px]">UPI: {acc.upi_id}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-[10px] text-zinc-500 font-semibold uppercase tracking-wider">Account Balance</p>
                      <p className="text-lg font-bold font-mono text-emerald-400 mt-0.5">₹{acc.balance.toLocaleString('en-IN')}</p>
                    </div>
                  </div>
                ))
              ) : (
                <div className="bg-zinc-950/40 border border-dashed border-zinc-800 text-center py-4 text-zinc-500 text-xs rounded-lg">
                  No active SBI savings account linked yet. Run the "Acquire Agent" flow to open one.
                </div>
              )}
            </div>

            {/* Customer Transactions Ledger */}
            <div>
              <h3 className="text-sm font-bold text-zinc-50 mb-2">Recent Transactions</h3>
              <div className="overflow-hidden border border-zinc-800 rounded-lg max-h-40 overflow-y-auto">
                <table className="w-full text-left border-collapse text-[11px]">
                  <thead>
                    <tr className="bg-zinc-950 text-zinc-500 border-b border-zinc-800 font-semibold">
                      <th className="p-2">Date</th>
                      <th className="p-2">Description</th>
                      <th className="p-2 text-right">Amount</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800 text-zinc-300">
                    {custTxns.map((txn, idx) => (
                      <tr key={idx} className="hover:bg-zinc-850">
                        <td className="p-2 font-mono text-zinc-500">{txn.date}</td>
                        <td className="p-2 flex flex-col">
                          <span className="font-medium text-zinc-200">{txn.description}</span>
                          <span className="text-[9px] text-zinc-500 font-mono">{txn.transaction_id}</span>
                        </td>
                        <td className={`p-2 text-right font-mono font-bold ${txn.type === 'DEBIT' ? 'text-rose-400' : 'text-emerald-400'}`}>
                          {txn.type === 'DEBIT' ? '-' : '+'}₹{parseFloat(txn.amount).toLocaleString('en-IN')}
                        </td>
                      </tr>
                    ))}
                    {custTxns.length === 0 && (
                      <tr>
                        <td colSpan="3" className="text-center py-4 text-zinc-500">No transactions recorded for this customer.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

          </div>
        )}
      </div>

    </div>
  );
}
