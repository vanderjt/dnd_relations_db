"""Shared exact-state editor with Simple recovery lifecycle."""
from .state_editor import StateEditor
from .task_draft import TaskDraft


class SimpleStateEditor(StateEditor):
    def __init__(self, parent, workspace, relationship_id, row, correction, event_id, recovered=None):
        def changed(message):
            self.original = self.values()
            self.draft.discard()
            workspace.app.refresh(message)
            workspace.remove_task()
        super().__init__(parent, workspace.database, changed, relationship_id, row, correction,
                         event_id, closed=workspace.close_task)
        self.workspace = workspace
        self.draft_key = f'task:state:{relationship_id}:{event_id}:{correction}'
        self.draft = TaskDraft(self, self.draft_key)
        if recovered:
            for key, value in recovered['values'].items():
                if key in self.variables:
                    self.variables[key].set(value)
            source = recovered['source_id']
            self.variables['source'].set(next((label for label, ident in self.sources.items() if ident == source), 'Missing source · restore character'))
            event = recovered['effective_event_id']
            if event is not None:
                self.variables['event'].set(next((label for label, ident in self.event_choices.items() if ident == event), 'Missing event · restore or reassign'))
            self.notes.delete('1.0', 'end')
            self.notes.insert('1.0', recovered['values']['notes'])
            self.error.set('Recovered draft · review the exact entry before saving')

    def update_save(self):
        self.save_button.state(['disabled' if self.correction and self.values() == self.original and self.step != 'review' else '!disabled'])

    def save(self):
        if self.correction and self.values() == self.original and self.step != 'review':
            return True
        return super().save()

    def draft_payload(self):
        return dict(task='state', relationship_id=self.relationship_id, row=self.row,
                    correction=self.correction, event_id=self.fixed_event_id,
                    source_id=self.sources.get(self.variables['source'].get()),
                    effective_event_id=self.event_choices.get(self.variables['event'].get()), values=self.values())

    def close(self):
        return self.workspace.close_task()

    def destroy(self):
        if hasattr(self, 'draft'):
            self.draft.close()
        super().destroy()


def recover_state(workspace, payload):
    db = workspace.database
    ident = payload['relationship_id']
    if ident not in {row['id'] for row in db.relationship_records()}:
        raise ValueError('Restore this connection and its characters from Trash before recovering its draft.')
    event = payload.get('event_id')
    if event is not None and event not in {row['id'] for row in db.events.list()}:
        raise ValueError('This draft refers to a missing event. Restore a backup to recover its exact context; draft retained.')
    return workspace.mount(lambda: SimpleStateEditor(workspace.host, workspace, ident, payload['row'], payload['correction'], event, payload))
