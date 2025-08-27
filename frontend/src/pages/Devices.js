import React from 'react';

const Devices = () => {
  const devices = [
    {
      id: 1,
      name: 'Kitchen Fridge',
      type: 'Refrigerator',
      location: 'Kitchen',
      status: 'active',
      power: '0.8 kW',
      efficiency: 'High'
    },
    {
      id: 2,
      name: 'Living Room AC',
      type: 'Air Conditioner',
      location: 'Living Room',
      status: 'active',
      power: '2.1 kW',
      efficiency: 'Medium'
    },
    {
      id: 3,
      name: 'Bedroom Light',
      type: 'Lighting',
      location: 'Bedroom',
      status: 'inactive',
      power: '0.1 kW',
      efficiency: 'High'
    },
    {
      id: 4,
      name: 'Office Computer',
      type: 'Computer',
      location: 'Home Office',
      status: 'active',
      power: '0.3 kW',
      efficiency: 'Medium'
    }
  ];

  const getStatusColor = (status) => {
    return status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800';
  };

  const getEfficiencyColor = (efficiency) => {
    switch (efficiency) {
      case 'High':
        return 'bg-green-100 text-green-800';
      case 'Medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'Low':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-900">Devices</h1>
      <p className="mt-2 text-gray-600">
        Monitor and manage your smart home devices
      </p>

      <div className="mt-6">
        <div className="bg-white shadow overflow-hidden sm:rounded-md">
          <ul className="divide-y divide-gray-200">
            {devices.map((device) => (
              <li key={device.id} className="px-6 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className="flex-shrink-0">
                      <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                        <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
                        </svg>
                      </div>
                    </div>
                    <div className="ml-4">
                      <div className="text-sm font-medium text-gray-900">
                        {device.name}
                      </div>
                      <div className="text-sm text-gray-500">
                        {device.type} • {device.location}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-4">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(device.status)}`}>
                      {device.status}
                    </span>
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getEfficiencyColor(device.efficiency)}`}>
                      {device.efficiency}
                    </span>
                    <div className="text-sm text-gray-900 font-medium">
                      {device.power}
                    </div>
                    <button className="text-blue-600 hover:text-blue-900 text-sm font-medium">
                      Details
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mt-6">
        <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium">
          Add New Device
        </button>
      </div>
    </div>
  );
};

export default Devices;
