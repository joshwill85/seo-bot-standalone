import React, { useState, useEffect } from 'react';
import { Button, Card, Badge, Tooltip, Modal, Progress, Grid, Typography, Space, message, Spin } from 'antd';
import { 
  SearchOutlined, 
  FileTextOutlined, 
  ToolOutlined, 
  LinkOutlined,
  EnvironmentOutlined,
  EyeOutlined,
  TrophyOutlined,
  BarChartOutlined,
  SettingOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;
const { Meta } = Card;

interface ServiceButton {
  button_id: string;
  button_text: string;
  button_description: string;
  category: string;
  estimated_completion_time: string;
  automation_level: string;
  prerequisites: string[];
  output_deliverables: string[];
  parameters_required: string[];
}

interface WorkflowExecution {
  execution_id: string;
  button_id: string;
  status: string;
  estimated_completion_time: string;
  workflow_steps: any[];
  created_at: string;
  progress?: {
    current: number;
    total: number;
    status: string;
  };
}

interface ServiceButtonsProps {
  projectId: string;
  userPermissions: string[];
}

const ServiceButtons: React.FC<ServiceButtonsProps> = ({ projectId, userPermissions }) => {
  const [serviceButtons, setServiceButtons] = useState<Record<string, ServiceButton[]>>({});
  const [activeExecutions, setActiveExecutions] = useState<Record<string, WorkflowExecution>>({});
  const [loading, setLoading] = useState(true);
  const [executingButton, setExecutingButton] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [executionModal, setExecutionModal] = useState<{
    visible: boolean;
    execution?: WorkflowExecution;
  }>({ visible: false });

  // Category icons mapping
  const categoryIcons = {
    keyword_research: <SearchOutlined />,
    content_strategy: <FileTextOutlined />,
    technical_seo: <ToolOutlined />,
    link_building: <LinkOutlined />,
    local_seo: <EnvironmentOutlined />,
    competitor_analysis: <EyeOutlined />,
    conversion_optimization: <TrophyOutlined />,
    analytics_reporting: <BarChartOutlined />,
    automation_management: <SettingOutlined />
  };

  // Automation level colors
  const automationColors = {
    instant: '#52c41a',
    background: '#1890ff',
    scheduled: '#fa8c16'
  };

  useEffect(() => {
    fetchDashboardLayout();
    fetchActiveExecutions();
    
    // Poll for execution updates every 5 seconds
    const interval = setInterval(fetchActiveExecutions, 5000);
    return () => clearInterval(interval);
  }, [projectId]);

  const fetchDashboardLayout = async () => {
    try {
      const response = await fetch('/api/v1/dashboard/dashboard-layout', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      });
      const data = await response.json();
      setServiceButtons(data.dashboard_layout);
    } catch (error) {
      console.error('Failed to fetch service buttons:', error);
      message.error('Failed to load service buttons');
    } finally {
      setLoading(false);
    }
  };

  const fetchActiveExecutions = async () => {
    try {
      const response = await fetch('/api/v1/dashboard/workflow-history?limit=10', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      });
      const data = await response.json();
      
      // Filter for active executions
      const active = data.workflow_history
        .filter((execution: any) => ['in_progress', 'queued'].includes(execution.status))
        .reduce((acc: any, execution: any) => {
          acc[execution.button_id] = execution;
          return acc;
        }, {});
      
      setActiveExecutions(active);
    } catch (error) {
      console.error('Failed to fetch active executions:', error);
    }
  };

  const executeWorkflow = async (buttonId: string, parameters: Record<string, any> = {}) => {
    setExecutingButton(buttonId);
    
    try {
      const response = await fetch('/api/v1/dashboard/execute-workflow', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          button_id: buttonId,
          parameters: {
            project_id: projectId,
            ...parameters
          },
          priority: 'normal'
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to execute workflow');
      }

      const execution = await response.json();
      
      // Update active executions
      setActiveExecutions(prev => ({
        ...prev,
        [buttonId]: execution
      }));

      // Show execution modal for background tasks
      if (execution.status === 'queued') {
        setExecutionModal({
          visible: true,
          execution: execution
        });
        message.success('Workflow started successfully');
      } else if (execution.status === 'completed') {
        message.success('Workflow completed successfully');
      }

      // Start polling for this execution
      pollExecutionStatus(execution.execution_id, buttonId);

    } catch (error: any) {
      console.error('Failed to execute workflow:', error);
      message.error(error.message || 'Failed to execute workflow');
    } finally {
      setExecutingButton(null);
    }
  };

  const pollExecutionStatus = async (executionId: string, buttonId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/v1/dashboard/workflow-status/${executionId}`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
            'Content-Type': 'application/json'
          }
        });
        
        const status = await response.json();
        
        // Update active executions
        setActiveExecutions(prev => ({
          ...prev,
          [buttonId]: { ...prev[buttonId], ...status }
        }));

        // Stop polling if completed or failed
        if (['completed', 'failed', 'SUCCESS', 'FAILURE'].includes(status.status)) {
          clearInterval(pollInterval);
          
          if (status.status === 'completed' || status.status === 'SUCCESS') {
            message.success(`${getButtonText(buttonId)} completed successfully`);
            // Remove from active executions after a delay
            setTimeout(() => {
              setActiveExecutions(prev => {
                const updated = { ...prev };
                delete updated[buttonId];
                return updated;
              });
            }, 3000);
          } else {
            message.error(`${getButtonText(buttonId)} failed: ${status.error || 'Unknown error'}`);
          }
        }
      } catch (error) {
        console.error('Failed to poll execution status:', error);
        clearInterval(pollInterval);
      }
    }, 3000);
  };

  const getButtonText = (buttonId: string): string => {
    for (const category of Object.values(serviceButtons)) {
      const button = category.find(b => b.button_id === buttonId);
      if (button) return button.button_text;
    }
    return buttonId;
  };

  const renderServiceButton = (button: ServiceButton) => {
    const isExecuting = executingButton === button.button_id;
    const activeExecution = activeExecutions[button.button_id];
    const hasActiveExecution = Boolean(activeExecution);

    let buttonStatus = 'default';
    let statusIcon = <PlayCircleOutlined />;
    let statusText = 'Run Now';

    if (isExecuting) {
      buttonStatus = 'loading';
      statusText = 'Starting...';
    } else if (hasActiveExecution) {
      if (activeExecution.status === 'completed' || activeExecution.status === 'SUCCESS') {
        buttonStatus = 'success';
        statusIcon = <CheckCircleOutlined />;
        statusText = 'Completed';
      } else if (activeExecution.status === 'failed' || activeExecution.status === 'FAILURE') {
        buttonStatus = 'danger';
        statusIcon = <ExclamationCircleOutlined />;
        statusText = 'Failed';
      } else {
        buttonStatus = 'processing';
        statusIcon = <ClockCircleOutlined />;
        statusText = 'Running...';
      }
    }

    return (
      <Card
        key={button.button_id}
        hoverable={!hasActiveExecution}
        className={`service-button-card ${hasActiveExecution ? 'executing' : ''}`}
        styles={{
          body: { padding: '16px' }
        }}
        actions={[
          <Tooltip title={button.button_description} key="info">
            <Button
              type={buttonStatus === 'default' ? 'primary' : buttonStatus as any}
              icon={statusIcon}
              loading={isExecuting}
              disabled={hasActiveExecution && activeExecution.status !== 'completed'}
              onClick={() => executeWorkflow(button.button_id)}
              block
            >
              {statusText}
            </Button>
          </Tooltip>
        ]}
      >
        <Meta
          title={
            <Space>
              {button.button_text}
              <Badge 
                color={automationColors[button.automation_level as keyof typeof automationColors]} 
                text={button.automation_level}
              />
            </Space>
          }
          description={
            <div>
              <Paragraph ellipsis={{ rows: 2 }} style={{ marginBottom: 8 }}>
                {button.button_description}
              </Paragraph>
              
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  ⏱️ {button.estimated_completion_time}
                </Text>
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  📋 {button.output_deliverables.length} deliverables
                </Text>
              </div>

              {hasActiveExecution && activeExecution.progress && (
                <div style={{ marginTop: 8 }}>
                  <Progress 
                    percent={Math.round((activeExecution.progress.current / activeExecution.progress.total) * 100)}
                    size="small"
                    status={activeExecution.status === 'failed' ? 'exception' : 'active'}
                  />
                  <Text style={{ fontSize: '11px', color: '#666' }}>
                    {activeExecution.progress.status}
                  </Text>
                </div>
              )}
            </div>
          }
        />
      </Card>
    );
  };

  const renderCategory = (categoryName: string, categoryData: any) => {
    const filteredButtons = selectedCategory === 'all' || selectedCategory === categoryName 
      ? categoryData.buttons 
      : [];

    if (filteredButtons.length === 0) return null;

    return (
      <div key={categoryName} style={{ marginBottom: 32 }}>
        <Title level={4} style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
          {categoryIcons[categoryName as keyof typeof categoryIcons]}
          {categoryData.category_title}
          <Badge count={filteredButtons.length} style={{ backgroundColor: '#52c41a' }} />
        </Title>
        
        <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
          {categoryData.category_description}
        </Text>

        <Grid.Row gutter={[16, 16]}>
          {filteredButtons.map((button: ServiceButton) => (
            <Grid.Col xs={24} sm={12} md={8} lg={6} key={button.button_id}>
              {renderServiceButton(button)}
            </Grid.Col>
          ))}
        </Grid.Row>
      </div>
    );
  };

  const categoryTabs = [
    { key: 'all', label: 'All Services', icon: <SettingOutlined /> },
    { key: 'keyword_research', label: 'Keywords', icon: <SearchOutlined /> },
    { key: 'content_strategy', label: 'Content', icon: <FileTextOutlined /> },
    { key: 'technical_seo', label: 'Technical', icon: <ToolOutlined /> },
    { key: 'link_building', label: 'Links', icon: <LinkOutlined /> },
    { key: 'local_seo', label: 'Local SEO', icon: <EnvironmentOutlined /> },
    { key: 'competitor_analysis', label: 'Competitors', icon: <EyeOutlined /> },
    { key: 'conversion_optimization', label: 'Conversion', icon: <TrophyOutlined /> },
    { key: 'analytics_reporting', label: 'Analytics', icon: <BarChartOutlined /> }
  ];

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>Loading SEO services...</div>
      </div>
    );
  }

  return (
    <div className="service-buttons-container">
      {/* Category Filter Tabs */}
      <div style={{ marginBottom: 24, borderBottom: '1px solid #f0f0f0', paddingBottom: 16 }}>
        <Space wrap>
          {categoryTabs.map(tab => (
            <Button
              key={tab.key}
              type={selectedCategory === tab.key ? 'primary' : 'default'}
              icon={tab.icon}
              onClick={() => setSelectedCategory(tab.key)}
              style={{ marginBottom: 8 }}
            >
              {tab.label}
            </Button>
          ))}
        </Space>
      </div>

      {/* Active Executions Summary */}
      {Object.keys(activeExecutions).length > 0 && (
        <Card style={{ marginBottom: 24, backgroundColor: '#f6ffed', borderColor: '#b7eb8f' }}>
          <Title level={5} style={{ margin: 0, color: '#389e0d' }}>
            🚀 Active Workflows ({Object.keys(activeExecutions).length})
          </Title>
          <div style={{ marginTop: 8 }}>
            {Object.entries(activeExecutions).map(([buttonId, execution]) => (
              <div key={buttonId} style={{ marginBottom: 4 }}>
                <Text>{getButtonText(buttonId)}</Text>
                <Text type="secondary" style={{ marginLeft: 8, fontSize: '12px' }}>
                  {execution.status === 'in_progress' ? '⏳ In Progress' : 
                   execution.status === 'queued' ? '📋 Queued' : 
                   execution.status}
                </Text>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Service Buttons by Category */}
      {Object.entries(serviceButtons).map(([categoryName, categoryData]) => 
        renderCategory(categoryName, categoryData)
      )}

      {/* Execution Status Modal */}
      <Modal
        title="Workflow Execution"
        open={executionModal.visible}
        onCancel={() => setExecutionModal({ visible: false })}
        footer={[
          <Button key="close" onClick={() => setExecutionModal({ visible: false })}>
            Close
          </Button>
        ]}
      >
        {executionModal.execution && (
          <div>
            <Paragraph>
              <strong>Workflow:</strong> {getButtonText(executionModal.execution.button_id)}
            </Paragraph>
            <Paragraph>
              <strong>Status:</strong> {executionModal.execution.status}
            </Paragraph>
            <Paragraph>
              <strong>Estimated Time:</strong> {executionModal.execution.estimated_completion_time}
            </Paragraph>
            
            {executionModal.execution.workflow_steps && (
              <div>
                <Title level={5}>Workflow Steps:</Title>
                {executionModal.execution.workflow_steps.map((step, index) => (
                  <div key={index} style={{ marginBottom: 8, padding: 8, background: '#f5f5f5', borderRadius: 4 }}>
                    <Text strong>Step {step.step}:</Text> {step.action}
                    <br />
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      Estimated time: {step.estimated_time}
                    </Text>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </Modal>

      <style>{`
        .service-button-card {
          transition: all 0.3s ease;
          border-radius: 8px;
        }
        
        .service-button-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }
        
        .service-button-card.executing {
          border-color: #1890ff;
          box-shadow: 0 0 8px rgba(24, 144, 255, 0.3);
        }
        
        .service-buttons-container .ant-card-meta-title {
          font-size: 14px;
          font-weight: 600;
        }
        
        .service-buttons-container .ant-card-meta-description {
          font-size: 12px;
        }
      `}</style>
    </div>
  );
};

export default ServiceButtons;