# -*- coding: utf-8 -*-

import requests
import json

from odoo import api, fields, models
from datetime import datetime
from dateutil import parser
from odoo.exceptions import UserError


class GithubTeam(models.Model):
    _name = "github.team"
    _description = "Github Team"
    _rec_name = 'name'

    name = fields.Char(required=True)
    github_user = fields.Char(required=True)
    github_token = fields.Char(required=True)
    organization = fields.Char(required=True)
    pr_ids = fields.One2many('pull.request', 'team')
    members = fields.Many2many('res.partner', string='Team Members')

    def fetch_pr(self):  
        session = requests.Session()

        for team in self:
            session.auth = (team.github_user, team.github_token)
            for member in team.members:
                for i in [1,2,3,4,5,6,7,8,9]:
                    url = f"https://api.github.com/search/issues?q=is:pr+org:{team.organization}+author:{member.github_user}&page={i}"
                    
                    if self._context.get('its_cron'):
                        url = url + "+state:open"
                    try:
                        response = session.get(url)
                        response.raise_for_status()
                    except UserError as e:
                        return e
                    for pr in response.json().get('items'):
                        partner = self.env['res.partner'].search([('github_user', '=', pr.get('user').get('login'))])
                        closed_date = datetime.strptime(pr.get('closed_at'), "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M") if (pr.get('closed_at')) else False
                        create_date = datetime.strptime(pr.get('created_at'), "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M")
                        state = 'draft' if pr.get('draft') else pr.get('state')
                        
                        vals = {
                            'state': state,
                            'closed_date': closed_date,
                            'title': pr.get('title'),
                            'draft': pr.get('draft'),
                            'body': pr.get('body'),
                            'author': partner and partner[0].id,
                            'author_name': pr.get('user').get('name'),
                            'team': team.id,
                            'comments_url': pr.get('comments_url'),
                            'timeline_url': pr.get('timeline_url'),
                            'html_url': pr.get('html_url')
                        }
     
                        pull_request = self.env['pull.request'].search([('git_id', '=', str(pr['id']))])
     
                        if pull_request:
                            pull_request.write(vals)

                        else:
                            vals.update({
                                'git_id':pr.get('id'),
                                'pr_number': pr.get('number'),
                                'pr_create_date': create_date,
                                })
                            pr = self.env['pull.request'].create(vals)
                            pr.fetch_comments()
                            pr.fetch_commits()

    def cron_fetch_pr(self):
        self.search([]).with_context(its_cron=True).fetch_pr()
                