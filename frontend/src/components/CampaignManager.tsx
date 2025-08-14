import { useState } from 'react'
import { Plus, Edit, Trash2, Play, Pause, BarChart3, Target, FileText, Search } from 'lucide-react'
import { mockCampaigns, mockSEOTasks, mockContentBriefs } from '@/data/mockData'

interface CampaignManagerProps {
  businessId: string
  businessName: string
  onClose: () => void
}

const CampaignCard = ({ campaign, onEdit, onDelete, onToggleStatus }: {
  campaign: any
  onEdit: (campaign: any) => void
  onDelete: (campaignId: string) => void
  onToggleStatus: (campaignId: string) => void
}) => {
  const tasks = mockSEOTasks.filter(t => t.campaign_id === campaign.id)
  const briefs = mockContentBriefs.filter(b => b.campaign_id === campaign.id)
  
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-800'
      case 'paused': return 'bg-yellow-100 text-yellow-800'
      case 'completed': return 'bg-blue-100 text-blue-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 mb-1">{campaign.name}</h3>
          <p className="text-sm text-gray-600 mb-2">{campaign.description}</p>
          <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(campaign.status)}`}>
            {campaign.status.charAt(0).toUpperCase() + campaign.status.slice(1)}
          </span>
        </div>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={() => onEdit(campaign)}
            className="p-2 text-gray-400 hover:text-florida-blue-600 transition-colors"
          >
            <Edit className="w-4 h-4" />
          </button>
          <button
            onClick={() => onToggleStatus(campaign.id)}
            className="p-2 text-gray-400 hover:text-florida-orange-600 transition-colors"
          >
            {campaign.status === 'active' ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          </button>
          <button
            onClick={() => onDelete(campaign.id)}
            className="p-2 text-gray-400 hover:text-red-600 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
        <div>
          <span className="text-gray-600">Keywords:</span>
          <span className="font-semibold text-gray-900 ml-1">{campaign.total_keywords}</span>
        </div>
        <div>
          <span className="text-gray-600">Difficulty:</span>
          <span className="font-semibold text-gray-900 ml-1">{campaign.avg_keyword_difficulty?.toFixed(1) || 'N/A'}</span>
        </div>
        <div>
          <span className="text-gray-600">Tasks:</span>
          <span className="font-semibold text-gray-900 ml-1">{tasks.length}</span>
        </div>
        <div>
          <span className="text-gray-600">Content:</span>
          <span className="font-semibold text-gray-900 ml-1">{campaign.content_pieces_published}/{campaign.content_pieces_planned}</span>
        </div>
      </div>

      {campaign.seed_keywords && campaign.seed_keywords.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="text-xs text-gray-600 mb-2">Seed Keywords:</div>
          <div className="flex flex-wrap gap-1">
            {campaign.seed_keywords.slice(0, 3).map((keyword: string, index: number) => (
              <span key={index} className="inline-block px-2 py-1 text-xs bg-florida-blue-100 text-florida-blue-800 rounded-full">
                {keyword}
              </span>
            ))}
            {campaign.seed_keywords.length > 3 && (
              <span className="inline-block px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded-full">
                +{campaign.seed_keywords.length - 3} more
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

const CampaignForm = ({ campaign, businessId, onSave, onCancel }: {
  campaign?: any
  businessId: string
  onSave: (campaignData: any) => void
  onCancel: () => void
}) => {
  const [formData, setFormData] = useState({
    name: campaign?.name || '',
    description: campaign?.description || '',
    seed_keywords: campaign?.seed_keywords?.join(', ') || '',
    competitors: campaign?.competitors?.join(', ') || '',
    content_pieces_planned: campaign?.content_pieces_planned || 10,
    status: campaign?.status || 'active'
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    const campaignData = {
      ...formData,
      business_id: businessId,
      seed_keywords: formData.seed_keywords.split(',').map(k => k.trim()).filter(k => k),
      competitors: formData.competitors.split(',').map(c => c.trim()).filter(c => c),
      total_keywords: 0,
      content_pieces_published: campaign?.content_pieces_published || 0,
      avg_keyword_difficulty: campaign?.avg_keyword_difficulty || 0,
      estimated_monthly_traffic: campaign?.estimated_monthly_traffic || 0,
      created_at: campaign?.created_at || new Date().toISOString()
    }
    
    onSave(campaignData)
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-semibold text-gray-900 mb-6">
          {campaign ? 'Edit Campaign' : 'Create New Campaign'}
        </h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Campaign Name
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-florida-blue-500 focus:border-florida-blue-500"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-florida-blue-500 focus:border-florida-blue-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Seed Keywords (comma-separated)
            </label>
            <textarea
              value={formData.seed_keywords}
              onChange={(e) => setFormData({ ...formData, seed_keywords: e.target.value })}
              placeholder="e.g., restaurant orlando, seafood dining, waterfront restaurant"
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-florida-blue-500 focus:border-florida-blue-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Competitor URLs (comma-separated)
            </label>
            <textarea
              value={formData.competitors}
              onChange={(e) => setFormData({ ...formData, competitors: e.target.value })}
              placeholder="e.g., https://competitor1.com, https://competitor2.com"
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-florida-blue-500 focus:border-florida-blue-500"
            />
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Planned Content Pieces
              </label>
              <input
                type="number"
                min="1"
                max="100"
                value={formData.content_pieces_planned}
                onChange={(e) => setFormData({ ...formData, content_pieces_planned: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-florida-blue-500 focus:border-florida-blue-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Status
              </label>
              <select
                value={formData.status}
                onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-florida-blue-500 focus:border-florida-blue-500"
              >
                <option value="active">Active</option>
                <option value="paused">Paused</option>
                <option value="completed">Completed</option>
              </select>
            </div>
          </div>
          
          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-sm font-medium text-white bg-florida-blue-600 border border-transparent rounded-md hover:bg-florida-blue-700 transition-colors"
            >
              {campaign ? 'Update Campaign' : 'Create Campaign'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function CampaignManager({ businessId, businessName, onClose }: CampaignManagerProps) {
  const [campaigns, setCampaigns] = useState(mockCampaigns.filter(c => c.business_id === businessId))
  const [showForm, setShowForm] = useState(false)
  const [editingCampaign, setEditingCampaign] = useState<any>(null)

  const handleCreateCampaign = () => {
    setEditingCampaign(null)
    setShowForm(true)
  }

  const handleEditCampaign = (campaign: any) => {
    setEditingCampaign(campaign)
    setShowForm(true)
  }

  const handleSaveCampaign = (campaignData: any) => {
    if (editingCampaign) {
      // Update existing campaign
      setCampaigns(prev => prev.map(c => 
        c.id === editingCampaign.id ? { ...c, ...campaignData } : c
      ))
      console.log('Updated campaign:', campaignData)
    } else {
      // Create new campaign
      const newCampaign = {
        ...campaignData,
        id: `camp-${Date.now()}`,
        created_at: new Date().toISOString()
      }
      setCampaigns(prev => [...prev, newCampaign])
      console.log('Created new campaign:', newCampaign)
    }
    setShowForm(false)
    setEditingCampaign(null)
  }

  const handleDeleteCampaign = (campaignId: string) => {
    if (window.confirm('Are you sure you want to delete this campaign? This action cannot be undone.')) {
      setCampaigns(prev => prev.filter(c => c.id !== campaignId))
      console.log('Deleted campaign:', campaignId)
    }
  }

  const handleToggleStatus = (campaignId: string) => {
    setCampaigns(prev => prev.map(c => {
      if (c.id === campaignId) {
        const newStatus = c.status === 'active' ? 'paused' : 'active'
        console.log(`Changed campaign ${campaignId} status to ${newStatus}`)
        return { ...c, status: newStatus }
      }
      return c
    }))
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-40">
      <div className="bg-white rounded-lg w-full max-w-6xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">SEO Campaigns</h2>
            <p className="text-sm text-gray-600">{businessName}</p>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={handleCreateCampaign}
              className="flex items-center px-4 py-2 text-sm font-medium text-white bg-florida-blue-600 rounded-md hover:bg-florida-blue-700 transition-colors"
            >
              <Plus className="w-4 h-4 mr-1" />
              New Campaign
            </button>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-80px)]">
          {campaigns.length === 0 ? (
            <div className="text-center py-12">
              <Target className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">No SEO Campaigns</h3>
              <p className="text-gray-600 mb-4">
                Create your first SEO campaign to start tracking keywords and optimizing content.
              </p>
              <button
                onClick={handleCreateCampaign}
                className="px-4 py-2 text-sm font-medium text-white bg-florida-blue-600 rounded-md hover:bg-florida-blue-700 transition-colors"
              >
                Create First Campaign
              </button>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Campaign Stats */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-florida-blue-50 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-florida-blue-900">{campaigns.length}</div>
                  <div className="text-sm text-gray-600">Total Campaigns</div>
                </div>
                <div className="bg-green-50 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-green-900">
                    {campaigns.filter(c => c.status === 'active').length}
                  </div>
                  <div className="text-sm text-gray-600">Active</div>
                </div>
                <div className="bg-florida-orange-50 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-florida-orange-900">
                    {campaigns.reduce((sum, c) => sum + (c.total_keywords || 0), 0)}
                  </div>
                  <div className="text-sm text-gray-600">Total Keywords</div>
                </div>
                <div className="bg-purple-50 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-purple-900">
                    {campaigns.reduce((sum, c) => sum + (c.content_pieces_published || 0), 0)}
                  </div>
                  <div className="text-sm text-gray-600">Content Published</div>
                </div>
              </div>

              {/* Campaign Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {campaigns.map((campaign) => (
                  <CampaignCard
                    key={campaign.id}
                    campaign={campaign}
                    onEdit={handleEditCampaign}
                    onDelete={handleDeleteCampaign}
                    onToggleStatus={handleToggleStatus}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Campaign Form Modal */}
      {showForm && (
        <CampaignForm
          campaign={editingCampaign}
          businessId={businessId}
          onSave={handleSaveCampaign}
          onCancel={() => {
            setShowForm(false)
            setEditingCampaign(null)
          }}
        />
      )}
    </div>
  )
}