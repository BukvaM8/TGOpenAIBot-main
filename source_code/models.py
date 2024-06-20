from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Dialogue(Base):
    __tablename__ = 'dialogues'
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, unique=True, index=True)
    messages = relationship("Message", back_populates="dialogue")


class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String)
    dialogue_id = Column(Integer, ForeignKey('dialogues.id'))
    dialogue = relationship("Dialogue", back_populates="messages")

